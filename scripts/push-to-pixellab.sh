#!/data/data/com.termux/files/usr/bin/bash
# Usage : bash push.sh [nom_fichier.plp ...]
#   Sans argument : push tous les PLP de output/ vers psd2plp_out/ (racine pixelLab)
#   Avec arguments : push les fichiers nommes vers psd2plp_out/
# REGLE : on n'ecrit JAMAIS dans pixelLab/presets/

OUT="/storage/emulated/0/pixelLab/psd2plp_out"
cd "$(dirname "$0")" || exit 1
mkdir -p "$OUT"

if [ $# -eq 0 ]; then
    cp output/*.plp "$OUT/" 2>/dev/null
    echo "Archive mise a jour : $OUT"
    ls "$OUT" | tail -5
else
    for f in "$@"; do
        if [ -f "output/$f" ]; then
            cp "output/$f" "$OUT/"
            echo "Pousse : $f -> $OUT"
        elif [ -f "$f" ]; then
            cp "$f" "$OUT/"
            echo "Pousse : $f -> $OUT"
        else
            echo "Introuvable : $f"
        fi
    done
fi
