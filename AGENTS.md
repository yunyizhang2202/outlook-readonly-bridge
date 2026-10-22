# Repository handoff rules

- Read README.md, START_HERE_FOR_GPT.md and docs/ADMIN_PERMISSIONS.md before troubleshooting.
- This is a public source repository. Never commit credentials, real email addresses, runtime config, mailbox IDs, mail bodies, screenshots, PST/OST files or raw diagnostic logs.
- All mailbox operations stay read-only. Do not add send/delete/move/mark-as-read, arbitrary shell, arbitrary COM operations or public unauthenticated HTTP endpoints.
- Use exact allowlists; missing config denies access. Do not silently broaden access.
- Do not weaken Outlook Object Model Guard, endpoint protections or organization policies.
- Distinguish Microsoft Entra consent, Windows elevation and OpenAI organization/workspace rights. Do not use generic elevation as a fix.
- Reuse existing working installations. Keep the Windows forward-slash MCP command fix.
- Test changes with `python -m unittest test_core.py test_config.py`; when dependencies are installed also run `python test_protocol.py`. Report actual outputs and platform limits.
- Do not claim Windows or end-to-end success from Linux tests.
- Coordinate in one issue using unique MESSAGE_ID and IN_REPLY_TO. An issue does not automatically wake another GPT. Do not post repetitive acknowledgements.
