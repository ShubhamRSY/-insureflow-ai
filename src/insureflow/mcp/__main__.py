"""Allow ``python -m insureflow.mcp`` to launch the MCP server (stdio)."""

from __future__ import annotations

import logging
import sys


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    from insureflow.mcp.server import create_mcp_server

    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
