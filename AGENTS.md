# 北門行政平台作業守則

## 備份與版本庫

- 所有本機備份一律存放在 `D:\backups\nghcc-nads26\` 或其日期時間子目錄，不得放在 Git 工作樹內。
- 每次修改前先確認 Git repository、目前 branch、remote 與 `git status`。
- 專案應連結 GitHub repository `peterchen9/nghcc-nads26`；若未設定 repository 或 remote，必須先提醒使用者。
- `.env`、密碼、SQL dump、`mysql_data`、media、log 與任何備份檔不得加入 Git。

## 正式環境安全

- 未經使用者明確授權，不得部署、重啟容器、修改正式資料庫、設定、權限或 Nginx。
- 執行正式環境命令前，先顯示命令及目標位置。
- 不得以刪除再重建的方式同步 `MenuItem`；選單更新必須保留既有 primary key。
- 不得在正式環境執行會批次刪除 `MenuItem` 的腳本或命令。
- 選單修改前後必須備份並核對 `MenuItem` 數量、使用者權限關聯總數，以及零權限的一般使用者數量；若權限關聯減少，立即停止部署並調查。
- 發現敏感資料時只報告，不自行修改、刪除或輪替。
