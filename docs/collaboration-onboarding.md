# 北門行政平台：新電腦與協作者上手指南

這份文件提供第一次在另一台電腦接手、開發或協作本專案時所需的共同背景。開始修改前，請先讀完本文件與 repository 根目錄的 `AGENTS.md`。

## 1. 專案概要

- Repository：`https://github.com/peterchen9/nghcc-nads26`
- 主要分支：`main`
- 技術：Python、Django 5、MySQL 8、Docker Compose
- Django 專案目錄：`nads26/`
- Django 設定：`nads26/nads26/`
- 功能模組：`nads26/modules/`
- 共用模板：`nads26/templates/`
- 靜態檔案：`nads26/static/`

主要模組如下：

| 模組 | 用途 |
| --- | --- |
| `accounts`、`menu` | 帳號、登入、選單與權限 |
| `eureka` | 會友與人員相關資料 |
| `staff` | 同工資料、請假與人事功能 |
| `facility`、`maintenance` | 場地與維修管理 |
| `budget` | 財務與預算相關功能 |
| `education` | 教育訓練與 QR Code |
| `file_center`、`pages` | 檔案中心、內容與媒體功能 |
| `hymns`、`humnos` | 詩歌與影音資源 |
| `power`、`network` | 電力與網路設備相關功能 |

更完整的功能與系統資訊請參考：

- `docs/platform-features.md`
- `docs/system-inventory.md`
- `docs/docker-production-layout.md`
- `docs/backup-and-restore-runbook.md`
- `docs/production-baseline.md`

## 2. 先理解哪些內容會同步

GitHub 只同步程式碼、migration、模板、測試與文件。以下內容不得提交到 Git，也不會自動出現在另一台電腦：

- `.env` 與所有密碼、token、secret
- MySQL 資料與 SQL dump
- `mysql_data/`
- `media/`、private media、NAS 檔案
- log
- 本機備份
- 正式環境設定與 Nginx 私有設定

因此「程式碼協作」使用 GitHub；「資料與秘密」必須透過另外核准的安全管道處理。

## 3. 新電腦第一次安裝

### 3.1 必要工具

建議安裝：

- Git
- Docker Desktop（最簡單的本機執行方式）
- Visual Studio Code 或其他編輯器
- Python 3.12（若不使用 Docker）

確認工具：

```powershell
git --version
docker --version
docker compose version
```

### 3.2 重新 clone

本專案曾重寫 Git 歷史以清除敏感資料。舊電腦若已有重寫前的 clone，請保留舊目錄作為臨時參考，但另開新目錄重新 clone；不要把舊歷史直接 merge 回來。

```powershell
cd C:\Users\<你的帳號>\Documents
git clone https://github.com/peterchen9/nghcc-nads26.git
cd nghcc-nads26
git switch main
git status
git remote -v
```

預期狀態應包含：

```text
On branch main
Your branch is up to date with 'origin/main'.
```

## 4. 建立本機環境設定

Compose 的 `env_file` 位於 `nads26/docker-compose.yml`，因此實際 `.env` 必須放在 `nads26/.env`：

```powershell
Copy-Item .env.example nads26\.env
notepad nads26\.env
```

`.env.example` 只包含 placeholder。請從核准的密碼管理或安全管道取得本機需要的值，不可從 Git 歷史、聊天內容或舊版程式碼找回密碼。

本機 Docker Compose 至少要確認：

- `DJANGO_SECRET_KEY` 使用新的隨機值
- `DJANGO_DEBUG=True` 僅限本機開發
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`
- `DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:26001`
- 本機 HTTP 開發可設定 `DJANGO_SECURE_COOKIES=False`
- `DB_HOST=db`
- `DB_PORT=3306`
- `DB_NAME=nads26db`
- 目前 Compose 建立的 MySQL 使用者為 `admin`，所以 `DB_USER=admin`
- `DB_PASSWORD` 與 `MYSQL_PASSWORD` 必須相同
- `MYSQL_ROOT_PASSWORD` 必須是另一組本機密碼

外部設備、NAS、舊資料庫或 Wi-Fi 相關設定若本次工作不需要，請保持空白或使用明確的非正式 placeholder，不要填入正式憑證。

## 5. 使用 Docker 啟動本機環境

以下命令只適用於新電腦的本機開發環境，不是正式環境部署命令：

```powershell
cd nads26
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

建立資料表：

```powershell
docker compose exec web python manage.py migrate
```

需要本機管理者帳號時：

```powershell
docker compose exec web python manage.py createsuperuser
```

開啟：`http://localhost:26001/`

查看 log：

```powershell
docker compose logs --tail 100 web
docker compose logs --tail 100 db
```

停止本機容器：

```powershell
docker compose stop
```

不要在不確定資料用途時執行 `docker compose down -v`，因為 `-v` 可能移除本機持久化資料。

## 6. 不使用 Docker 的 Python 開發方式

```powershell
cd nads26
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

若要使用 SQLite 做不涉及正式資料的本機開發，可在目前 PowerShell session 設定：

```powershell
$env:DJANGO_SECRET_KEY='test-only-not-for-production'
$env:DJANGO_SECURE_COOKIES='False'
$env:DB_ENGINE='django.db.backends.sqlite3'
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## 7. 修改前先了解專案

每次開始工作時依序執行：

```powershell
git status --short --branch
git branch --show-current
git remote -v
git pull --ff-only origin main
```

閱讀順序建議：

1. `AGENTS.md`：備份、正式環境與 Git 安全守則。
2. 本文件：新電腦與協作流程。
3. `docs/platform-features.md`：功能全貌。
4. `docs/system-inventory.md`：服務、資料與環境關係。
5. `nads26/nads26/urls.py`：主要 URL 入口。
6. 對應的 `nads26/modules/<module>/urls.py`、`views.py`、`models.py` 與測試。

要快速搜尋功能：

```powershell
rg "關鍵字" nads26\modules nads26\templates
rg --files nads26\modules
```

## 8. 建議的 Git 協作方式

不要直接在 `main` 同時開發多項工作。每項工作建立自己的分支：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/<簡短功能名稱>
```

修改過程中隨時檢查：

```powershell
git status
git diff
```

提交前：

```powershell
git diff --check
git status --short
```

只加入本次工作的檔案：

```powershell
git add <檔案1> <檔案2>
git diff --cached
git commit -m "清楚描述本次變更"
git push -u origin feature/<簡短功能名稱>
```

再從 GitHub 建立 Pull Request，讓另一台電腦或另一位協作者檢查後合併。合併後在其他電腦同步：

```powershell
git switch main
git pull --ff-only origin main
```

## 9. 測試與基本驗證

Docker 環境：

```powershell
cd nads26
docker compose exec web python manage.py check
docker compose exec web python manage.py test
```

本機 Python 環境：

```powershell
cd nads26
$env:DJANGO_SECRET_KEY='test-only-not-for-production'
$env:DJANGO_SECURE_COOKIES='False'
python manage.py check
python manage.py test
```

如果完整測試太慢，至少執行本次修改模組的測試。測試失敗時不要直接推送，先記錄失敗測試名稱與錯誤原因。

## 10. 資料庫 migration 與選單權限

- model 有變更時使用 `python manage.py makemigrations <module>`，並檢查產生的 migration。
- migration 檔應提交到 Git。
- 不可用「刪除後重建」同步 `MenuItem`。
- 不可執行會批次刪除 `MenuItem` 的腳本。
- 正式環境選單更新前後必須核對 `MenuItem` 數量、權限關聯總數與零權限一般使用者數量。
- 未經明確授權，不可在正式環境執行 migration、資料修正或容器重啟。

## 11. 如何把工作交給 Codex 或其他 AI 協作者

在新電腦開啟專案後，可先提供以下指示：

```text
請先完整閱讀 repository 根目錄的 AGENTS.md，
再閱讀 docs/collaboration-onboarding.md、docs/platform-features.md
與 docs/system-inventory.md。先檢查 Git branch、remote、status，
只分析目前問題，不要部署、重啟正式容器或修改正式資料。
```

接著描述：

- 你想修改的功能與頁面。
- 預期行為與目前行為。
- 是否只需診斷，或可以直接修改。
- 是否允許建立 migration。
- 哪些測試必須通過。
- 明確說明這是本機、測試環境或正式環境。

## 12. 正式環境安全界線

正式環境不是一般協作測試環境。未經專案負責人明確授權，不得：

- 部署或同步程式到正式主機。
- 重啟、重建或刪除容器。
- 修改正式資料庫、migration 狀態、設定或權限。
- 修改 Nginx。
- 複製、提交或顯示正式密碼與 secret。

若發現疑似敏感資料，只報告檔案位置與類型，不要在 issue、PR、commit 或聊天中貼出實際值。

## 13. 新協作者完成檢查表

- [ ] 已重新 clone 最新 `main`。
- [ ] 已閱讀 `AGENTS.md` 與本指南。
- [ ] `origin` 指向 `peterchen9/nghcc-nads26`。
- [ ] `nads26/.env` 已建立且未被 Git 追蹤。
- [ ] 已能啟動本機服務。
- [ ] 已能開啟本機首頁。
- [ ] 已成功執行 `manage.py check`。
- [ ] 已了解 Git 不包含正式資料庫、media、NAS 檔案與秘密。
- [ ] 已使用獨立 feature branch 開始工作。
- [ ] 已確認不會在未授權下操作正式環境。
