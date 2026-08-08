# 2026-08-08 秘密輪替紀錄

## 範圍

在建立並驗證正式主機與 `D:\backups\nghcc-nads26\` 雙端完整備份後，完成下列處理：

- Django `SECRET_KEY` 改由 `DJANGO_SECRET_KEY` 環境變數提供並完成輪替。
- nads26 MySQL `root` 與 `admin` 密碼完成輪替。
- datacenter MySQL `peter` 密碼完成輪替。
- 正式主機 `peterchen` SSH 密碼完成輪替。
- Compose、Django settings、資料同步腳本及網路設備程式移除硬編碼密碼。
- DB 與 Web 容器以新環境重新建立，未執行 migration、collectstatic 或 image build。
- Git 歷史中的已曝光值以 `git-filter-repo` 清除；改寫前完整 Git bundle 僅保存於 D 槽。

實際新秘密只保存於 D 槽受限 ACL 的 recovery file，不得加入 GitHub、文件、issue、PR 或 log。

## 驗證

- 正式網址與 localhost HTTP 均回應 200。
- nads26 與 datacenter DB 新憑證均通過唯讀連線測試。
- 使用者選單權限關聯維持 881 筆。
- 無選單權限的非 superuser 維持 1 人。
- media 41,899、static 34、private_media 10、rooms 29，與備份來源數量完全一致。
- SQL gzip 完整可讀，包含 184 個 `CREATE TABLE`、3 個 `CREATE DATABASE` 與完成標記。
- 最終備份 manifest 26/26 通過。

## 尚需設備端人工處理

- `172.20.60.241` 的 NADS25 舊憑證在輪替前已無法登入，因此未修改該外部資料庫；`NADS25_DB_PASSWORD` 保持空值，相關腳本會安全停止。
- NU840 可使用既有憑證登入，但管理介面使用不受信任 TLS 憑證，且登入頁未提供可驗證的改密碼端點。設備端密碼需由管理者在受信任的設備管理介面人工輪替，再更新正式 `.env`。

## 後續規則

- 禁止在程式、Compose 或 settings 提供秘密 literal fallback。
- 正式環境秘密只存放於 `.env`；GitHub 只保存 `.env.example` placeholder。
- 發布前必須掃描目前 tree 與全部 Git 歷史，並確認備份、SQL 與權限基線。
