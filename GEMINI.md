# psd2plp

This extension exposes a local MCP server (`psd2plp-mcp`) that generates editable PixelLab `.plp` projects and manages fonts (search, Fontsource/Google Fonts download, TTF/OTF import).

- Install the server first: `uv tool install git+https://github.com/Lemuelnk/psd2plp`.
- Follow the `prompt-to-plp` skill for the generation workflow.
- Download a font with `download_font` before using its `font_family` in `generate_plp`.
- Structural validation (`validate_plp`) does not prove that PixelLab opens the file: say so.
