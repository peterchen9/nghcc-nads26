# 北門行政平台（nghcc-nads26）

北門行政平台是部署於內部 Docker 主機、由 Nginx 提供 HTTPS 入口的 Django 應用程式。本 repository 保存可審查的程式碼與非敏感維運文件；正式環境的密碼、`.env`、資料庫、上傳媒體、log 與備份不得進入 Git。

平台整合會友與牧區、同工人事、聚會出席、場地與設備、維修、財務、教育課程、禮拜資源及文件管理。功能依登入者、超級管理員及個別選單授權顯示；完整功能與狀態請見[平台功能說明](docs/platform-features.md)。

## 正式環境摘要

- 正式網址：`https://ad.nghcc.org.tw/`
- 正式主機：`192.168.16.240`（主機名 `gino25`）
- Compose 專案：`nads26`
- 正式程式位置：`/home/apps1/nads26`
- Compose 設定：`/home/apps1/nads26/docker-compose.yml`
- Web 容器：`nads26-web`，主機 `26001` 對容器 `8000`
- DB 容器：`nads26db`，MySQL 8.0，主機 `33069` 對容器 `3306`
- Docker network：`nads26_default`
- Nginx vhost：`/etc/nginx/sites-enabled/ad.nghcc.org.tw.conf`

## 文件

- [平台功能說明](docs/platform-features.md)
- [系統盤點](docs/system-inventory.md)
- [Docker 正式環境配置](docs/docker-production-layout.md)
- [備份與還原手冊](docs/backup-and-restore-runbook.md)
- [正式環境基線](docs/production-baseline.md)

## 安全原則

使用 `.env.example` 建立環境設定，實際值由受控秘密儲存提供。執行部署、migration、靜態檔收集、容器重建或還原前，必須另行核准並先完成可驗證備份。
