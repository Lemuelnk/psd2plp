#!/usr/bin/env bash
# Copie le SKILL.md de reference dans chaque plugin / extension (a relancer apres modification).
set -euo pipefail
cd "$(dirname "$0")/.."
src=plugins/skills/prompt-to-plp/SKILL.md
# Claude Code, ChatGPT/Codex/Copilot (plugins) et Gemini CLI (racine du depot)
for dir in plugins/claude plugins/chatgpt .; do
  mkdir -p "$dir/skills/prompt-to-plp"
  cp "$src" "$dir/skills/prompt-to-plp/SKILL.md"
done
echo "skills synchronises"
