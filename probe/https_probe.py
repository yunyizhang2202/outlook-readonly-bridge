"""Disposable, single-user OAuth/HTTP probe. No Outlook imports or mailbox tools.

Not a production authorization server. In-memory state expires on restart.
Run behind a user-approved HTTPS forwarding service; bind loopback only.
"""
import argparse
import getpass
import hashlib
import html
import secrets
import time
from urllib.parse import urlsplit

import uvicorn
from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizeError, OAuthAuthorizationServerProvider,
    RegistrationError, TokenError, construct_redirect_uri,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.auth import OAuthToken
from mcp.types import ToolAnnotations
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse

SCOPE = "probe:read"
SECURITY_HEADERS = {
    "Cache-Control": "no-store", "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
}


def validate_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.port not in (None, 443)):
        raise ValueError("Use only a public HTTPS origin without path, credentials, query or custom port")
    return "https://" + parsed.hostname.lower()


def allowed_callback(uri):
    # Actual ChatGPT callbacks, as documented by OpenAI. No arbitrary redirect hosts.
    p = urlsplit(str(uri))
    prefix = "/connector/oauth/"
    suffix = p.path[len(prefix):] if p.path.startswith(prefix) else ""
    return (p.scheme == "https" and p.hostname == "chatgpt.com" and p.port in (None, 443)
            and not p.username and not p.password and not p.query and not p.fragment
            and (p.path == "/connector_platform_oauth_redirect"
                 or (suffix and all(c.isascii() and (c.isalnum() or c in "_-") for c in suffix))))


class ProbeProvider(OAuthAuthorizationServerProvider):
    def __init__(self, origin, passphrase):
        if len(passphrase) < 24:
            raise ValueError("Choose a new probe-only passphrase of at least 24 characters")
        self.origin = validate_origin(origin)
        self.resource = self.origin + "/mcp"
        self.password_hash = hashlib.sha256(passphrase.encode()).digest()
        self.clients, self.pending, self.codes, self.tokens = {}, {}, {}, {}
        self.failures = []

    def cleanup(self):
        now = time.time()
        for table in (self.pending, self.codes, self.tokens):
            for key, value in list(table.items()):
                deadline = value["expires"] if isinstance(value, dict) else value.expires_at
                if deadline <= now:
                    del table[key]
        self.failures = [t for t in self.failures if t > now - 300]

    async def get_client(self, client_id):
        return self.clients.get(client_id)

    async def register_client(self, client_info):
        self.cleanup()
        if len(self.clients) >= 50:
            raise RegistrationError(error="invalid_client_metadata", error_description="Probe client limit reached; restart probe")
        if not client_info.redirect_uris or not all(allowed_callback(u) for u in client_info.redirect_uris):
            raise RegistrationError(error="invalid_redirect_uri", error_description="Only documented ChatGPT HTTPS callbacks are allowed")
        self.clients[client_info.client_id] = client_info

    async def authorize(self, client, params):
        self.cleanup()
        if params.resource != self.resource or params.scopes != [SCOPE]:
            raise AuthorizeError(error="invalid_request", error_description="Use the probe resource and probe:read scope")
        if not allowed_callback(params.redirect_uri) or len(self.pending) >= 50:
            raise AuthorizeError(error="invalid_request", error_description="Callback rejected or probe is busy")
        request_id = secrets.token_urlsafe(32)
        self.pending[request_id] = {"client_id": client.client_id, "params": params,
                                    "expires": time.time() + 300, "csrf": None}
        return self.origin + "/probe-login?request=" + request_id

    async def load_authorization_code(self, client, authorization_code):
        self.cleanup()
        code = self.codes.get(authorization_code)
        return code if code and code.client_id == client.client_id else None

    async def exchange_authorization_code(self, client, authorization_code):
        self.cleanup()
        code = self.codes.pop(authorization_code.code, None)
        if code is None or code.client_id != client.client_id or len(self.tokens) >= 50:
            raise TokenError(error="invalid_grant", error_description="Code expired, consumed or probe full")
        token = secrets.token_urlsafe(32)
        self.tokens[token] = AccessToken(token=token, client_id=client.client_id, scopes=code.scopes,
                                        expires_at=int(time.time()) + 900, resource=self.resource,
                                        subject="probe-owner")
        return OAuthToken(access_token=token, token_type="Bearer", expires_in=900, scope=SCOPE)

    async def load_access_token(self, token):
        self.cleanup()
        return self.tokens.get(token)

    async def load_refresh_token(self, client, refresh_token):
        return None

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        raise TokenError(error="invalid_grant", error_description="Probe has no refresh tokens; reconnect")

    async def revoke_token(self, token):
        self.tokens.pop(token.token, None)


def create_app(origin, passphrase):
    provider = ProbeProvider(origin, passphrase)
    host = urlsplit(provider.origin).hostname
    mcp = FastMCP(
        "Authenticated connectivity probe", stateless_http=True, json_response=True,
        auth_server_provider=provider,
        auth=AuthSettings(issuer_url=provider.origin, resource_server_url=provider.resource,
                          validate_token_resource=True, required_scopes=[SCOPE],
                          client_registration_options=ClientRegistrationOptions(
                              enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE])),
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                                      allowed_hosts=[host, host + ":443"],
                                                      allowed_origins=[provider.origin]),
    )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                          idempotentHint=True, openWorldHint=False))
    def bridge_ping() -> dict:
        """Return a constant test result. Never accesses mail, files, shell or network."""
        return {"ok": True, "message": "AUTHENTICATED_MCP_PROBE_OK", "mail_access": False}

    @mcp.custom_route("/probe-login", methods=["GET", "POST"])
    async def login(request):
        provider.cleanup()
        request_id = request.query_params.get("request", "")
        pending = provider.pending.get(request_id)
        if pending is None:
            return PlainTextResponse("Request missing or expired. Restart sign-in.", status_code=400, headers=SECURITY_HEADERS)
        if request.method == "GET":
            csrf = secrets.token_urlsafe(32)
            pending["csrf"] = csrf
            callback = html.escape(str(pending["params"].redirect_uri))
            body = ("<!doctype html><html><head><meta charset='utf-8'><title>Probe sign-in</title></head><body>"
                    "<h1>Connectivity probe sign-in</h1><p>This probe has no mailbox access.</p>"
                    f"<p>Callback: {callback}</p><p>Scope: probe:read (fixed test string only)</p>"
                    "<form method='post'><label>Probe passphrase <input name='passphrase' type='password' "
                    "autocomplete='current-password' required maxlength='512'></label>"
                    f"<input type='hidden' name='csrf' value='{csrf}'>"
                    "<button type='submit'>Sign in and allow probe</button></form></body></html>")
            response = HTMLResponse(body, headers=SECURITY_HEADERS)
            response.set_cookie("probe_csrf", csrf, secure=True, httponly=True, samesite="lax", max_age=300)
            return response
        if request.headers.get("origin") not in (None, provider.origin):
            return PlainTextResponse("Origin rejected", status_code=403, headers=SECURITY_HEADERS)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 8192:
                return PlainTextResponse("Form too large", status_code=413, headers=SECURITY_HEADERS)
        from urllib.parse import parse_qs
        form = parse_qs(raw.decode("utf-8", errors="replace"))
        csrf = form.get("csrf", [""])[0]
        expected = pending.get("csrf")
        if (not expected or not secrets.compare_digest(csrf.encode(), expected.encode())
                or not secrets.compare_digest(request.cookies.get("probe_csrf", "").encode(), expected.encode())):
            return PlainTextResponse("Sign-in verification failed", status_code=403, headers=SECURITY_HEADERS)
        if len(provider.failures) >= 10:
            return PlainTextResponse("Too many attempts. Wait five minutes.", status_code=429, headers=SECURITY_HEADERS)
        password = form.get("passphrase", [""])[0]
        if not secrets.compare_digest(hashlib.sha256(password.encode()).digest(), provider.password_hash):
            provider.failures.append(time.time())
            return PlainTextResponse("Passphrase rejected. Return to sign-in.", status_code=401, headers=SECURITY_HEADERS)
        # No await between consuming the request and storing its one-use code.
        if provider.pending.pop(request_id, None) is None:
            return PlainTextResponse("Request already consumed", status_code=400, headers=SECURITY_HEADERS)
        params = pending["params"]
        code = secrets.token_urlsafe(32)
        provider.codes[code] = AuthorizationCode(
            code=code, scopes=[SCOPE], expires_at=time.time() + 60,
            client_id=pending["client_id"], code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri, redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=provider.resource, subject="probe-owner")
        response = RedirectResponse(construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state),
                                    status_code=303, headers=SECURITY_HEADERS)
        response.delete_cookie("probe_csrf", secure=True, httponly=True, samesite="lax")
        return response

    return mcp.streamable_http_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-origin", required=True, help="HTTPS origin of the approved forwarder; no /mcp path")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    origin = validate_origin(args.public_origin)
    if not 1024 <= args.port <= 65535:
        parser.error("Use a loopback port in 1024..65535")
    password = getpass.getpass("Create a NEW probe-only passphrase (24+ characters, hidden): ")
    if password != getpass.getpass("Repeat probe passphrase (hidden): "):
        parser.error("Passphrases differ")
    app = create_app(origin, password)
    password = ""
    print("Probe only: no Outlook import or mail tools. MCP path is /mcp. Stop with Ctrl+C.")
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False, log_level="warning",
                proxy_headers=False, forwarded_allow_ips="")


if __name__ == "__main__":
    main()
