# PLP engine integration

## Why this integration is an adapter, not a blind copy

The upstream `Lemuelnk/psd2plp` project provides a useful PLP model, reader,
writer and format notes. Its current reader maps only selected object fields
into a simplified model; its writer then reconstructs objects from that model.
That is useful for conversion, but it is not a lossless editor for arbitrary
PixelLab projects.

The plugin therefore adds a preservation-oriented archive layer. It retains
the complete `data.plab` document and every ZIP entry as raw payloads. Unknown
root keys, unknown object keys, resource paths and binary resource bytes are
not projected away during a read/rewrite cycle.

## Implemented in this branch

- ZIP entry/path validation with limits on entry count, total expanded size,
  per-entry size and suspicious compression ratios.
- UTF-8 JSON parsing of `data.plab` with structural checks for
  `objectsIds` and `objectsBundle`.
- Preservation of unknown root/object properties and binary resources.
- Round-trip writing that verifies each uncompressed archive entry by SHA-256
  before replacing the destination file.
- A new MCP tool, `roundtrip_plp`, to create a verified copy of a PLP from
  `input/` or `output/` into `output/`.

## Deliberate boundaries

- This does not prove that PixelLab itself will open the resulting archive.
  App-level open, save and reopen tests are still required.
- It does not yet change native text font bindings. The upstream writer's
  absolute resource paths and the plugin's font catalog metadata need a
  target-app-generated fixture before that behavior is enabled.
- It does not replace the AI design planner or the current native object
  generator. It adds a safe preservation layer alongside them.
- The current `psd2plp` reader remains unsuitable as a lossless edit model
  until object-level raw properties and all references are preserved.

## Upstream reference

- Repository: https://github.com/Lemuelnk/psd2plp
- Inspected branch: `main`
- Inspected commit: `b6cf0f8abfcf98f029dd3523154df2dd7e1ac3e2`
- Relevant references: `docs/PLP_FORMAT.md`,
  `src/psd2plp/pixellab/model.py`,
  `src/psd2plp/pixellab/reader.py`,
  `src/psd2plp/pixellab/writer.py`
- Upstream project declares Apache-2.0. No upstream source file is copied
  verbatim by this preservation adapter.
