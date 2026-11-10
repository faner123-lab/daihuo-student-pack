#!/usr/bin/env bash
# 把素材包放到固定位置 ~/学员素材包，并把所有技能装进 Claude（已装过的会被更新，不影响别的技能）
set -e
here="$(cd "$(dirname "$0")" && pwd)"
pack="$HOME/学员素材包"
mkdir -p "$pack"
cp -R "$here/学员素材包/." "$pack/"
echo "素材包已放到：$pack"
dest="$HOME/.claude/skills"
mkdir -p "$dest"
for d in "$here"/学员素材包/技能/*/; do
  cp -R "$d" "$dest/"
  echo "已安装技能：$(basename "$d")"
done
echo "完成，请重启 Claude。以后直接说「用 ip-daihuo-video-studio（或 3d-story-daihuo-studio）技能做一条带货视频」即可。"
