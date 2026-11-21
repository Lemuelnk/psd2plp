---
name: prompt-to-plp
description: Use when the user wants to create a native, editable PixelLab .plp project from a text prompt, select fonts, import font files, or inspect and validate an existing PLP file.
---

# Prompt-to-PLP and Font Engine workflow

## Goal

Turn a design brief into a PixelLab `.plp` project with independent native text and primitive shape objects. Use the Font Engine to find coherent type families and variants. Preserve editable text as the default.

The bundled MCP server is a **local stdio tool**. It writes generated projects to `output/`. It does not deploy a cloud service and is not available in ChatGPT mobile unless the host supports and runs local plugin processes.

## Font selection workflow

1. Identify the poster style, text role, language and hierarchy.
2. Call `recommend_fonts` for the role (headline/title/body); use `search_fonts` to inspect alternatives.
3. Use no more than 2–3 families in one poster. Prefer a display face for a short headline, a complementary serif/sans family for supporting text, and a highly readable body face.
4. Run `sync_fontsource_catalog` when online to refresh provider metadata; then check `get_font_details` for availability and variants. Do not assume that a catalog record means the binary is downloaded or installed in PixelLab.
5. Call `download_font` for a TTF variant when needed. The `auto` provider prefers Fontsource after metadata synchronization and otherwise uses Google Fonts. Set `provider` to `fontsource` or `google_fonts` to choose explicitly. Fontsource's TTF is fetched from its documented CDN endpoint; Google Fonts downloads retain the repository license file.
6. For custom files, place a TTF/OTF in `input/fonts/` and call `import_custom_font` with the file's actual license. Do not fabricate or infer license rights.
7. Keep typography editable. Do not outline text unless the user explicitly requests a non-editable fidelity fallback.

## Critical native PLP font limitation

The writer now serializes downloaded TTFs into `res/` and writes a `textTextFont.interval1.textsIntervalsFont` resource reference. This is the current writer contract; it has not yet been verified against a native custom-font PLP produced by the target PixelLab app version.

When `font_family` is included in a `generate_plp` text object, the engine resolves the requested downloaded TTF face and embeds its bytes in `res/`; the writer points the text font interval to that resource. The serialization is implemented, but actual PixelLab compatibility must still be checked by opening, saving and reopening the generated project on the target device. If the family has not been downloaded, generation returns an actionable error rather than silently substituting another font.

## Generation workflow

1. Identify canvas dimensions, exact copy, hierarchy, style, palette and object placements.
2. If dimensions are omitted, ask one concise clarification or use a common format only when clearly implied.
3. Plan a grid, margins and text fitting.
4. Pass geometry in source-canvas pixels; the engine converts it to the 708-unit reference space.
5. Use signed ARGB or `#RRGGBB` / `#AARRGGBB` colors.
6. Call `generate_plp`; array order is bottom-to-top.
7. Call `validate_plp` after generation. Report structural validation separately from the still-required PixelLab device test.
8. Clearly distinguish structural validation from a successful open/save test in PixelLab.

## Font catalog and licensing

- Starter catalog: 150 curated Google Fonts families. `sync_fontsource_catalog` verifies matching Fontsource IDs and records weights, styles, subsets, categories and versions.
- Downloaded Fontsource and Google Fonts TTFs are stored under `data/fonts/downloaded/`; Google Fonts downloads retain the repository license file. Review Fontsource package licensing before redistribution.
- Custom TTF/OTF files are stored under `data/fonts/custom/`; only TTF files are currently embedded by the generator.
- The importer's license field is a user declaration, not legal verification.
- Only TTF/OTF are accepted for custom imports; WOFF/WOFF2 and TTC are rejected because PixelLab compatibility is not established.

## Current supported PLP scope

- Canvas, solid background, editable text and primitive shape objects.
- Shape types: `rect`, `oval`, `tri1`.
- Basic text size, color, alignment, rotation, opacity and spacing.
- Downloaded TTF embedding and font-resource reference generation (PixelLab device compatibility pending).

## Not yet supported or verified

- PixelLab open/save/reopen compatibility of downloaded custom font resources.
- Whether PixelLab loads and preserves the generated TTF resource reference in the target app version.
- PixelLab's behavior when a project is opened on a device without the selected font.
- Full fidelity round-trip editing of arbitrary PLP projects.
- Images and advanced effects.

Never silently approximate unsupported behavior as native PixelLab functionality.
