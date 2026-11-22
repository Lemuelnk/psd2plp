#!/usr/bin/env bash
# Copie le SKILL.md de reference dans chaque plugin (a relancer apres modification).
set -euo pipefail
cd "$(dirname "$0")/.."
src=plugins/skills/prompt-to-plp/SKILL.md
for dir in plugins/claude; do
  mkdir -p "$dir/skills/prompt-to-plp"
  cp "$src" "$dir/skills/prompt-to-plp/SKILL.md"
done
echo "skills synchronises"
