# Pocapoca 故事村網站

繪本／插畫工作者 Poca（鄭夙雅）的作品網站。

## 每兩週發新節目時要做的事

1. 照平常一樣在 Firstory 發布節目。簡介裡的插畫網址寫 `https://www.pocapocastoryvillage.com/ep185`（換成這一集的集數）。
2. 把這一集的插畫放進 `podcast插畫/EP185/`，檔名 `01.jpg`、`02.jpg`……
3. 打開 GitHub Desktop，左下角 Summary 寫「EP185 插畫」，按 **Commit to main**，再按上方的 **Push origin**。

網站每天早上 6 點也會自動到 Firstory 檢查有沒有新節目。

## 資料夾說明

| 資料夾 | 內容 |
|---|---|
| `site/` | 網站本身（首頁、作品、About、Podcast 頁面和圖片） |
| `podcast插畫/` | 每一集 Podcast 的插畫 |
| `data/overrides.json` | 手動修正某一集的資料（例如插畫舊網址貼錯） |
| `scripts/` | 自動產生網站的小程式 |
| `.github/workflows/` | GitHub 自動執行的設定（每天更新網站、搬移 Wix 插畫） |

## 更新 About（關於我）

1. 打開「關於我」資料夾，修改 `about-中文.txt`（英文版是 `about-English.txt`）。
2. 每一筆一行：日期 + 空格 + 內容，新的寫在最上面；【 】裡的標題不要改。
3. 存檔後用 GitHub Desktop 上傳（Commit to main → Push origin），約 2 分鐘網站就更新。
4. 英文檔沒寫到的新項目，英文版會先顯示中文。之後在英文檔加一行同樣日期的英文就好。

## 桌曆預購頁（pocapocastoryvillage.com/calendar）

- **改文字、價格、截止日**：打開「桌曆/預購設定.txt」修改，存檔後用 GitHub Desktop Commit → Push。
- **換照片**：把照片放進「桌曆/照片」，照檔名順序排（01、02…），第一張也是分享預覽圖。
- **開關預購**：設定檔的「開放預購：是／準備中／否」。「準備中」時首頁不顯示按鈕，預購頁顯示「即將開放」。過了截止日也會自動關閉，首頁的「桌曆預購中」按鈕會一起消失。
- **訂單去哪裡**：網站的表單會送到 Google 表單「2027 桌曆」，所以訂單一樣出現在原本的 Google 試算表。
- ⚠️ 如果在 Google 表單**新增或刪除題目**、或改用**另一份新表單**，網站的表單也要跟著改（請 Claude 幫忙）。只改題目文字沒關係。
