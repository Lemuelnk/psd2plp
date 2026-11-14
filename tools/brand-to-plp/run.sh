#!/data/data/com.termux/files/usr/bin/bash
# Wrapper : lance build-social-templates.py adapte, en pointant ROOT
# vers le vrai projet lnk-brand.
#
# Configurable via LNK_BRAND_ROOT (defaut : ~/storage/shared/LNK_WORKS/lnk-brand)

: "${LNK_BRAND_ROOT:=$HOME/storage/shared/LNK_WORKS/lnk-brand}"
export LNK_BRAND_ROOT

if [ ! -d "$LNK_BRAND_ROOT" ]; then
    echo "ERREUR : LNK_BRAND_ROOT introuvable : $LNK_BRAND_ROOT" >&2
    echo "Definir la variable : export LNK_BRAND_ROOT=/chemin/vers/lnk-brand" >&2
    exit 1
fi

cd "$(dirname "$0")"
exec python3 adapted/build-social-templates.py "$@"
