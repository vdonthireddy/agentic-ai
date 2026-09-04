"""Model Context Protocol (MCP) Server package."""

from .server import app
from .router import router

__all__ = [
    "app",
    "router"
]
