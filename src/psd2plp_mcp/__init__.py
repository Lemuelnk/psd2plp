"""MCP server for psd2plp — plugin host for ChatGPT/Claude.

Exposes the psd2plp engine as MCP tools:
- generate_plp : spec JSON -> .plp (via psd2plp.spec.builder)
- inspect_plp  : structural inspection
- validate_plp : structure + core relationship validation
- roundtrip_plp: lossless read/write preservation
- Font Engine  : catalog, search, download, custom import
"""

__version__ = "0.1.0"
