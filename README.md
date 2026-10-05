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
