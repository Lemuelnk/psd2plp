#!/data/data/com.termux/files/usr/bin/bash
# Wrapper : lance build-social-templates.py adapte, en pointant ROOT
# vers le vrai projet lnk-brand.
export LNK_BRAND_ROOT="$HOME/storage/shared/LNK_WORKS/lnk-brand"
cd "$(dirname "$0")"
exec python3 adapted/build-social-templates.py "$@"
