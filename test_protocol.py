import asyncio
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parameters = StdioServerParameters(command=sys.executable,
                                      args=[str(Path(__file__).with_name("server.py"))])
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.list_tools()
            names = {t.name for t in result.tools}
            assert names == {"outlook_list_accounts", "outlook_list_folders", "outlook_search_emails",
                             "outlook_read_email", "outlook_read_attachment"}
            assert all(t.annotations.readOnlyHint for t in result.tools)
            # Linux cannot attach Windows COM; this must be a real tool error, not fake mail.
            if sys.platform != "win32":
                response = await session.call_tool("outlook_list_accounts", {})
                assert response.isError
                assert "Windows classic Outlook" in str(response.content)
            invalid = await session.call_tool("outlook_read_email", {})
            assert invalid.isError
            print("MCP initialization, discovery, read-only annotations and error handling: PASS")


if __name__ == "__main__":
    asyncio.run(main())

