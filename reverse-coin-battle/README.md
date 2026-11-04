# 逆轉金幣 Reverse Coin Battle（逆転バリバリバース 對戰遊戲）

> 測試版推廣版本 請勿銷售利用｜遊戲版權歸 BANDAI 萬代所有

依官方取扱説明書 Ver.1.1.2 エキスパートルール製作的粉絲對戰遊戲，內含全部 101 枚金幣資料。

| 資料夾 | 內容 |
|---|---|
| `docs/` | 網站版（3D／2D，手機可玩，含線上對戰）。開啟 GitHub Pages（Settings → Pages → Branch: main、資料夾 `/docs`）就能用網址玩 |
| `python-2d/` | Python 2D 桌面版（pygame-ce），Windows 雙擊 `執行遊戲.bat` |
| `windows-3d/` | 3D 電腦版：雙擊 `安裝到電腦.bat` 建立桌面捷徑，不需網路 |
| `android/` | Android Studio 專案（WebView 單機版），Build → Build APK |
| `web-source/` | 網頁版原始碼與打包腳本（`build_offline.py`、`build_2d_web.py`） |

## 遊戲重點
- 後拉發射（像彈弓）＋精準度條、撞球式碰撞與旋轉（可關閉）
- 每回合 18 秒、全場 8 分鐘（時間到比開場 M 值合計，少者勝）
- 雙人同機、對戰電腦、兩支手機線上對戰（PeerJS 點對點）
- 圖解規則、音效與背景音樂（`sounds/` 可自行替換）
