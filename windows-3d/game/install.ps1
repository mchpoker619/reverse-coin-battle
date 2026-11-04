# 逆轉金幣 3D 電腦版安裝：複製到 %LOCALAPPDATA%\ReverseCoin3D，建立桌面與開始功能表捷徑
# 測試版推廣版本 請勿銷售利用
$ErrorActionPreference = 'Stop'
$src  = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $env:LOCALAPPDATA 'ReverseCoin3D'
$name = '逆轉金幣 3D'
try {
  Write-Host "安裝到 $dest ..."
  if ((Resolve-Path $src).Path.TrimEnd('\') -ne $dest.TrimEnd('\')) {
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    New-Item -ItemType Directory -Path $dest | Out-Null
    Copy-Item (Join-Path $src '*') $dest -Recurse -Force
  }

  $html = Join-Path $dest 'game\ReverseCoin3D.html'
  $icon = Join-Path $dest 'game\icon.ico'
  $url  = 'file:///' + ($html -replace '\\', '/')

  # 找 Edge／Chrome（用 App 視窗開啟，沒有網址列，像一般程式）
  $browser = $null
  foreach ($exe in 'msedge.exe', 'chrome.exe') {
    foreach ($root in 'HKLM:', 'HKCU:') {
      $k = "$root\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\$exe"
      if (-not $browser -and (Test-Path $k)) {
        $p = (Get-ItemProperty $k).'(default)'
        if ($p -and (Test-Path $p)) { $browser = $p }
      }
    }
  }

  $sh = New-Object -ComObject WScript.Shell
  $targets = @(
    (Join-Path ([Environment]::GetFolderPath('Desktop')) "$name.lnk"),
    (Join-Path ([Environment]::GetFolderPath('Programs')) "$name.lnk")
  )
  foreach ($lnk in $targets) {
    $s = $sh.CreateShortcut($lnk)
    if ($browser) {
      $s.TargetPath = $browser
      $s.Arguments = "--app=`"$url`" --start-maximized"
    } else {
      $s.TargetPath = Join-Path $dest '執行遊戲.bat'
      $s.WindowStyle = 7
    }
    $s.WorkingDirectory = $dest
    $s.IconLocation = $icon
    $s.Description = '逆轉金幣 3D（測試版推廣版本 請勿銷售利用）'
    $s.Save()
  }
  Write-Host ''
  Write-Host '安裝完成！桌面和開始功能表都有「逆轉金幣 3D」捷徑，不需要網路。'
  if (-not $browser) { Write-Host '（沒找到 Edge／Chrome，會用預設瀏覽器開啟）' }
  Write-Host '要移除：執行安裝資料夾裡的「解除安裝.bat」，或在本資料夾執行它。'
  Start-Process -FilePath $targets[0]
} catch {
  Write-Host "[錯誤] $($_.Exception.Message)" -ForegroundColor Red
  Write-Host '請把這個視窗截圖給我。'
}
