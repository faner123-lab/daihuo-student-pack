#!/usr/bin/env bash
set -e
dest="$HOME/.claude/skills"
mkdir -p "$dest"
cp -R "$(dirname "$0")/学员素材包/技能/ip-daihuo-video-studio" "$dest/"
echo "已安装到 $dest/ip-daihuo-video-studio ，请重启 Claude。"
