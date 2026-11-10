# 把素材包放到固定位置 %USERPROFILE%\学员素材包，并把所有技能装进 Claude（已装过的会被更新，不影响别的技能）
$pack = Join-Path $env:USERPROFILE "学员素材包"
New-Item -ItemType Directory -Force -Path $pack | Out-Null
Copy-Item -Recurse -Force (Join-Path $PSScriptRoot "学员素材包\*") $pack
Write-Host "素材包已放到：$pack"
$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem -Directory (Join-Path $PSScriptRoot "学员素材包\技能") | ForEach-Object {
  Copy-Item -Recurse -Force $_.FullName $dest
  Write-Host "已安装技能：$($_.Name)"
}
Write-Host "完成，请重启 Claude。以后直接说「用 ip-daihuo-video-studio（或 3d-story-daihuo-studio）技能做一条带货视频」即可。"
