$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Recurse -Force (Join-Path $PSScriptRoot "学员素材包\技能\ip-daihuo-video-studio") $dest
Write-Host "已安装到 $dest\ip-daihuo-video-studio ，请重启 Claude。"
