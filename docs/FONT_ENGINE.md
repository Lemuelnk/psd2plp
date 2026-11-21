# LNK Studio — PixelLab AI Generator Font Engine

**Target release:** 0.2.2  
**Status:** Catalog, recommendation, Fontsource metadata sync, Fontsource/Google Fonts TTF download, custom TTF/OTF import and downloaded-TTF resource embedding implemented. Actual PixelLab open/save compatibility still requires a device test.

## 1. Goals

- Give the generator a searchable starter library of 150 type families.
- Recommend families by visual direction and text role.
- Track family metadata, variants, source and license state.
- Refresh provider metadata from Fontsource.
- Download compatible TTF files from the Google Fonts repository.
- Import user-supplied TTF/OTF files with explicit license declarations.
- Preserve native editable text in PLP projects.
- Never invent an undocumented PLP font property.

## 2. Architecture

```text
Design brief
    │
    ▼
Font Intelligence
    ├── style classifier / tags
    ├── role matcher (headline, title, body, caption)
    └── pairing policy (max 2–3 families)
    │
    ▼
Font Catalog API
    ├── 150-family seed catalog
    ├── Fontsource metadata synchronization
    └── LNK custom family records
    │
    ▼
Font Asset Manager
    ├── Fontsource API + jsDelivr TTF download
    ├── Google Fonts repository TTF download + license file
    ├── custom TTF/OTF import + SHA-256
    └── variant and local-availability tracking
    │
    ▼
PLP Compatibility Layer
    ├── validate intended family/weight/style
    ├── write sidecar font manifest (implemented)
    └── apply native PixelLab font reference (not yet implemented)
    │
    ▼
PLP Writer → editable .plp
```

## 3. Source responsibilities

| Source | Responsibility | Current implementation |
|---|---|---|
| Google Fonts repository | TTF binary assets and each family's license file | `download_font` downloads a selected TTF variant and license text |
| Fontsource API/CDN | Family IDs, weights, styles, subsets, versions and published TTF variants | `sync_fontsource_catalog` refreshes metadata; `download_font(provider=fontsource)` fetches a selected TTF face |
| LNK custom library | User-provided proprietary or separately licensed typefaces | `import_custom_font` validates and stores TTF/OTF files locally |

Fontsource package IDs are only marked verified after a successful metadata sync. The package candidate alone is not proof that a package or variant exists. Fontsource can now supply TTF assets directly through its documented API/CDN. Google Fonts remains available as a second TTF source.

## 4. Catalog schema

Each family record contains:

- `id`, `family`, `category`, `tags`
- `providers`, `google_fonts_slug`
- `fontsource_package_candidate`, `fontsource_status`
- `license`, `license_status`
- `availability`, `variants`, `custom`
- after sync: `fontsource_id`, `fontsource_weights`, `fontsource_styles`, `fontsource_subsets`, `fontsource_type`, `fontsource_category`, `fontsource_variable`, `fontsource_version`, `fontsource_last_modified`

`catalog.seed.json` is the immutable starter seed. `catalog.json` is created on first use and stores synchronized metadata and imported custom families. Do not overwrite `catalog.json` from the seed after user imports or provider syncs.

## 5. MCP tool contracts

| Tool | Purpose | Important inputs |
|---|---|---|
| `search_fonts` | Search family name, category and style tags | `query`, `category`, `limit`, `include_custom` |
| `recommend_fonts` | Rank font families for a design direction and text role | `style`, `usage`, `language`, `limit` |
| `get_font_details` | Read one family and its variants/provider/license state | `family_id` |
| `sync_fontsource_catalog` | Refresh Fontsource metadata | no required arguments |
| `download_font` | Download one TTF variant from Fontsource or Google Fonts | `family_id`, `weight`, `style`, `provider`, `subset` |
| `import_custom_font` | Import a custom TTF/OTF from `input/fonts/` | `filename`, `license_name`, optional family/designer/weight/style |
| `generate_plp` | Generate a PLP and optionally record intended font selections | per-text `font_family`, `font_weight`, `font_style` |

## 6. Storage layout

```text
font_library/
├── catalog.seed.json
├── catalog.json                 # runtime mutable index
├── downloaded/<google-slug>/    # Google Fonts TTF + license file
└── custom/<family-slug>/        # imported TTF/OTF files

input/fonts/                     # import staging area (shared with MCP server)
output/<project>.plp
output/<project>.plp.fonts.json  # intended font selections, not embedded in PLP
```

## 7. Native PLP compatibility decision

The inspected LNK Studio writer currently emits an empty `textTextFont` object. No native PixelLab font object or resource schema has yet been proven from a PixelLab-generated project containing a custom font.

Therefore:

1. Keep the PLP text objects native and editable.
2. A downloaded TTF is now embedded in `res/` and referenced through the writer's `textTextFont.interval1.textsIntervalsFont` resource path.
3. This is the writer's current serialization contract, not yet proof of compatibility with every PixelLab version.
4. Compare a generated file with a PixelLab-generated reference project containing a custom font.
5. Validate by opening, saving, closing and reopening the generated PLP in PixelLab on the target device.

The sidecar is an implementation bridge, not a claim that the PLP already uses the chosen font.

## 8. Security and licensing

- Custom imports accept only `.ttf` and `.otf` SFNT binaries; WOFF/WOFF2 and TTC are rejected.
- Font file size is limited to 32 MiB for imports.
- Google Fonts download is restricted to the official `raw.githubusercontent.com/google/fonts` repository and checks redirect host.
- Downloaded assets are limited to 16 MiB each.
- Custom filenames are restricted to a single file under `input/fonts/`; traversal and symlink escape are rejected.
- SHA-256 identifies duplicates and stored variants.
- Every custom import requires an explicit license declaration. The declaration is user-supplied and is not independently legally verified.
- Google Fonts license text is retained next to downloaded assets.

## 9. Verification

Automated tests cover:

- 150 unique seed families
- search and style/role recommendations
- custom TTF import and SFNT parsing
- rejection of path traversal
- mocked Google Fonts metadata/TTF/license download
- mocked Fontsource metadata synchronization
- MCP initialize, tool discovery and tool calls
- PLP generation, font manifest creation and structural validation

Still required:

- Live Fontsource API sync and TTF download in the deployed runtime
- Live Google Fonts TTF download in the deployed runtime
- PixelLab open/save/reopen test for generated PLP
- Confirmation of the font resource path against a native PixelLab reference file
- Android test for missing fonts and family fallback

## 10. Mobile/cloud deployment boundary

This package still uses a local Python MCP stdio process. Updating the plugin source does not make that process remotely reachable from ChatGPT Android. A later cloud release must host the same font/catalog/PLP services behind authenticated remote MCP endpoints and persistent object storage. Do not expose custom font uploads publicly or make private fonts world-readable by default.
