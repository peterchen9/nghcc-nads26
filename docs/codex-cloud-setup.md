# Codex Cloud 設定與跨電腦協作

本文件說明如何把 GitHub repository `peterchen9/nghcc-nads26` 作為北門行政平台的程式碼主版本，並在不同電腦或 Codex Cloud 中安全地維護。第一次在新電腦操作時，也要閱讀 [`collaboration-onboarding.md`](collaboration-onboarding.md) 與 repository 根目錄的 [`AGENTS.md`](../AGENTS.md)。

## 1. 儲存與執行邊界

- GitHub：保存程式碼、migration、測試與非敏感文件，是跨電腦同步的唯一主版本。
- Codex Cloud：依 branch 或 commit 建立隔離容器，適合分析、修改、測試與建立 Pull Request。
- Windows 本機：需要 Docker Desktop、完整本機測試資料或內網資源時使用。
- 正式主機 `.240`：只供經核准的備份、驗證與部署；Codex Cloud 不得直接操作正式環境。

GitHub 與 Codex Cloud 都不得保存正式 `.env`、資料庫、SQL dump、`mysql_data/`、`media/`、log、備份、SSH key 或設備密碼。

## 2. 啟用前安全閘門

建立 Cloud environment 前先確認：

- GitHub repository visibility 已設為 **Private**。
- GitHub 只授權 Codex 存取 `peterchen9/nghcc-nads26` 等確實需要的 repository。
- `main` 是最新且工作樹乾淨。
- `.env`、備份與執行資料均受 `.gitignore` 排除。
- 不把正式秘密填入 Cloud environment variables 或 setup script。
- 任何已曝光秘密都已輪替，且已依 `AGENTS.md` 完成目前 tree 與 Git 歷史掃描。

Repository visibility 必須由 repository 管理者在 GitHub 設定中確認。若仍為 Public，先停止 Cloud environment 上線作業，不要把正式資料或秘密加入環境。

## 3. 建議的 Codex Cloud environment

在 Codex 的 environment settings 建立一個環境：

| 欄位 | 建議值 |
| --- | --- |
| Environment name | `nghcc-nads26` |
| Repository | `peterchen9/nghcc-nads26` |
| Default branch | `main` |
| Working directory | repository root |
| Agent internet access | Off；只有明確需要外部文件或套件時再限縮開啟 |

Setup script：

```bash
set -euo pipefail
python -m pip install --upgrade pip
python -m pip install -r nads26/requirements.txt
```

供不連正式資料的基本 Django 檢查使用之 environment variables：

```text
DJANGO_SECRET_KEY=test-only-not-for-production
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_SECURE_COOKIES=False
DB_ENGINE=django.db.backends.sqlite3
```

這些值只能用於隔離測試。不要在 Codex Cloud 設定正式 DB、NAS、SSH、Wi-Fi、Hikvision、NADS25、NU840 或其他內網設備憑證。

## 4. 第一次 Cloud 驗證

Cloud environment 建立後，第一個 task 只做唯讀檢查：

```text
請先完整閱讀 AGENTS.md、docs/codex-cloud-setup.md、
docs/collaboration-onboarding.md 與 docs/system-inventory.md。
確認 branch、remote 與 git status，然後執行不連正式服務的 Django system check。
不要部署、不要連線 192.168.16.240、不要修改資料庫、容器、Nginx 或權限。
```

建議驗證命令：

```bash
cd nads26
python manage.py check
```

若功能測試依賴 MySQL、media、NAS 或其他內網資源，應在本機隔離環境處理，不要以正式資料補進 Cloud environment。

## 5. 每項工作的標準流程

1. 從最新 `main` 建立一個工作分支。
2. 一個分支只處理一項明確工作。
3. 先閱讀 `AGENTS.md` 與相關模組、測試及文件。
4. 在隔離環境修改並執行相關檢查。
5. 檢視 diff，確認沒有秘密、資料檔或非本次工作內容。
6. 建立 Pull Request，不直接覆蓋 `main`。
7. PR 經檢查並合併後，其他電腦再同步最新 `main`。
8. 正式部署另開工作階段，先備份並取得明確授權。

## 6. 不同電腦的同步方式

新電腦第一次使用：

```powershell
git clone https://github.com/peterchen9/nghcc-nads26.git
cd nghcc-nads26
git switch main
git status --short --branch
git remote -v
```

每次開始工作：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/<簡短工作名稱>
```

完成並合併 PR 後，其他電腦同步：

```powershell
git switch main
git pull --ff-only origin main
```

不要用 OneDrive、隨身碟或手動複製 Git 工作目錄來合併不同電腦的修改；跨電腦程式碼同步一律透過 branch、commit 與 Pull Request。

## 7. 正式環境限制

Codex Cloud 的成功測試不代表已獲准部署。正式主機為 `192.168.16.240`，實際程式位置為 `/home/apps1/nads26`；所有正式操作仍須遵守 `AGENTS.md`、備份手冊及以下限制：

- 未經明確授權，不連線、不部署、不重啟容器。
- 不執行 migration、collectstatic、資料修正或權限更新。
- 不修改 Nginx。
- 不把正式憑證帶入 Cloud environment。
- 涉及 `MenuItem` 時必須保留 primary key 並核對權限關聯基線。
