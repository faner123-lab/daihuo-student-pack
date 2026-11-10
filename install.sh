#!/usr/bin/env bash
# 把素材包里所有风格的技能装进 Claude（已装过的会被更新，不影响别的技能）
set -e
dest="$HOME/.claude/skills"
mkdir -p "$dest"
for d in "$(dirname "$0")"/学员素材包/技能/*/; do
  cp -R "$d" "$dest/"
  echo "已安装：$(basename "$d")"
done
echo "完成，请重启 Claude。"
