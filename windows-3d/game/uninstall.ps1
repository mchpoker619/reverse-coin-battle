# 逆轉金幣 3D 電腦版：移除捷徑與安裝資料夾
$name = '逆轉金幣 3D'
$dest = Join-Path $env:LOCALAPPDATA 'ReverseCoin3D'
foreach ($lnk in @(
    (Join-Path ([Environment]::GetFolderPath('Desktop')) "$name.lnk"),
    (Join-Path ([Environment]::GetFolderPath('Programs')) "$name.lnk"))) {
  if (Test-Path $lnk) { Remove-Item $lnk -Force }
}
Set-Location $env:TEMP
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Write-Host '已移除逆轉金幣 3D。'
