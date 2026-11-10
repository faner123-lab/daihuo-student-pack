# 把素材包里所有风格的技能装进 Claude（已装过的会被更新，不影响别的技能）
$dest = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem -Directory (Join-Path $PSScriptRoot "学员素材包\技能") | ForEach-Object {
  Copy-Item -Recurse -Force $_.FullName $dest
  Write-Host "已安装：$($_.Name)"
}
Write-Host "完成，请重启 Claude。"
