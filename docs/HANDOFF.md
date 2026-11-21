# HANDOFF — continuer le projet sans assistance

Ce document est concu pour reprendre le travail a froid, sans contexte
prealable. Il couvre : ou on en est, quoi faire ensuite, comment
debugger, et les pieges deja identifies.

Derniere mise a jour : 2026-11-21
Version psd2plp : 0.2.0

---

## 1. Etat du projet en une page

### Ce qui marche

| Feature | Commande | Statut |
|---|---|---|
| PSD -> PLP | `psd2plp convert fichier.psd -o out.plp` | OK |
| SVG -> PLP | `psd2plp convert fichier.svg -o out.plp` | OK (formes natives rect/oval/tri + raster) |
| Spec JSON -> PLP | `psd2plp from-spec spec.json -o out.plp` | OK (text, shapes, images, multi-couleurs) |
| Serveur MCP | `psd2plp-mcp` (stdio JSON-RPC) | OK (10 tools) |
| Font engine | via MCP `search_fonts`, `download_font` | OK (catalogue 150 familles) |
| Roundtrip PLP | via MCP `roundtrip_plp` | OK (lossless) |
| Inspect/validate PLP | via CLI/MCP | OK |

### Ce qui ne marche pas / pas encore

- **Ombres, gradients, glow** : pas implementes dans le spec
- **Wrap automatique du texte** : utiliser `\n` manuellement
- **Fonts PSD natives** : les calques texte PSD utilisent la police par
  defaut, pas la police du PSD (fichier TTF pas extrait du PSD)
- **SVG paths complexes** : rasterises (limitation PixelLab)
- **Apps PWA et Android native** : placeholders, migration future

### Repos GitHub

| Repo | Statut | Role |
|---|---|---|
| `Lemuelnk/psd2plp` | Public | Moteur + MCP + plugins (ce repo) |
| `Lemuelnk/Psd2plpG` | Prive | PWA + APK Capacitor (a migrer plus tard) |
| `Lemuelnk/Psd2plp-app` | Prive | Android natif Kotlin (a migrer plus tard) |
| `Lemuelnk/Lnk-brand` | Prive | Branding LNK Studio (separe) |

### Arborescence locale

    ~/lnk-projects/psd2plp/           Code source (ce repo)
    ~/storage/shared/LNK_WORKS/
      psd2plp_data/                   Assets lourds (PSD, PLP, output)
      lnk-brand/                      Projet branding (fonts TTF, logos)
    /storage/emulated/0/pixelLab/
      psd2plp_out/                    PLP deplies pour test dans PixelLab

---

## 2. Installer et tester en 5 minutes

    cd ~/lnk-projects/psd2plp
    pip install -e .

    # Test 1 : CLI
    psd2plp --help

    # Test 2 : serveur MCP
    echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' | timeout 5 psd2plp-mcp

    # Test 3 : generation spec -> PLP
    psd2plp from-spec examples/specs/poster_demo.json -o output/test.plp

    # Test 4 : ouvrir dans PixelLab
    cp output/test.plp /storage/emulated/0/pixelLab/psd2plp_out/

Si les 4 tests passent, tout fonctionne. Sinon, voir section 5 (debug).
