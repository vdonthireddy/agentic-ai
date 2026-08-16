"""Entry point for python -m llm_gateway.
Supports both HTTP (uvicorn) and Stdio transports.
"""

import sys
import os
import argparse
import uvicorn

# Ensure parent directory in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_gateway.config import config
from llm_gateway.stdio_gateway import main as run_stdio_server


def main():
    parser = argparse.ArgumentParser(description="LLM Gateway Server")
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=config.transport,
        help="Transport layer protocol: http or stdio (default: from config/env)"
    )
    parser.add_argument("--host", default=config.host, help="HTTP host")
    parser.add_argument("--port", type=int, default=config.port, help="HTTP port")
    
    args, _ = parser.parse_known_args()

    if args.transport == "stdio":
        run_stdio_server()
    else:
        uvicorn.run(
            "llm_gateway.app:app",
            host=args.host,
            port=args.port,
            log_level="info"
        )


if __name__ == "__main__":
    main()
