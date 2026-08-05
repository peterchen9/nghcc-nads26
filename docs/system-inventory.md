# 系統盤點

盤點日期：2026-08-05（Asia/Taipei）

## 服務入口與來源

| 項目 | 實際值 |
| --- | --- |
| 正式網址 | `https://ad.nghcc.org.tw/` |
| 正式主機 | `192.168.16.240`（`gino25`） |
| 程式來源 | `/home/apps1/nads26` |
| Compose file | `/home/apps1/nads26/docker-compose.yml` |
| Compose project | `nads26` |
| Nginx vhost symlink | `/etc/nginx/sites-enabled/ad.nghcc.org.tw.conf` |
| Nginx vhost target | `/etc/nginx/sites-available/ad.nghcc.org.tw.conf` |

Compose labels 與容器 bind mount 均確認 `/home/apps1/nads26` 是目前執行來源；Web 的 `/app` 直接 bind 至該目錄。

## 應用程式模組

2026-08-05 正式程式快照包含 216 條 URL、50 個資料模型、86 個模板及 14 個管理命令。主要 Django 模組如下：

| 模組 | 用途 |
| --- | --- |
| `accounts`、`menu` | 帳號、登入、使用者資料與動態選單授權 |
| `eureka` | 會友、牧區、同工、休假、出席、輪班與座位圖 |
| `staff` | 同工個人資料、密碼、休假、行事曆及費用申請入口 |
| `facility`、`maintenance` | 場地預約、巡檢、定期保養、維修與牧養報告 |
| `budget` | 預算、銀行、基金、團契與奉獻統計 |
| `education` | 課程、課堂、錄音、補課、文件與 QR Code |
| `file_center`、`pages` | 參考資料、內容頁、媒體、洗禮、安息禮與會議紀錄 |
| `hymns`、`humnos` | 詩歌資料與網路影音 |
| `power`、`network` | 電力報告、LAN 與 WLAN 盤點 |

完整使用者功能與已知施工中項目見 [`docs/platform-features.md`](platform-features.md)。

## 容器與持久化資料

| 容器 | Image | Port | Mount | Network |
| --- | --- | --- | --- | --- |
| `nads26-web` | `nads26-web` | `26001:8000` | `/home/apps1/nads26:/app` | `nads26_default` |
| `nads26db` | `mysql:8.0` | `33069:3306` | `/home/apps1/nads26/mysql_data:/var/lib/mysql` | `nads26_default` |

另有 local volume `nads26_nas_share`，盤點時未掛載至上述兩個執行中容器；其 driver option 可能含敏感連線資訊，只保存在受限制的 inspect 備份中。

## 資料基線

- `media`：約 12 GiB，盤點時計 41,899 個檔案。
- `static`：約 38 MiB，盤點時計 34 個檔案。
- `_rooms`：約 20 MiB，盤點時計 29 個檔案。
- `mysql_data`：約 432 MiB；為執行中 MySQL 實體資料，不應作為一致性還原的唯一來源。
- 既有 `backups`：約 11 GiB。

數量是盤點時點快照；以每次備份目錄內的 inventory 與 checksum 為該次權威紀錄。

本次 inventory 的 `media -xdev` 計數為 33,862；跨 filesystem 計數為 41,899。`media.tar.gz` 內含 41,899 個檔案，證明封包包含該 media 樹下跨 filesystem 的資料。`static` 與 `_rooms` 封包數量分別為 34 與 29，與來源相符。

## Nginx 路由

HTTPS vhost 將 `/` 反向代理至 `http://127.0.0.1:26001`，並傳遞 Host、來源 IP、forwarded protocol 與 WebSocket headers。HTTP port 80 由 Certbot 管理的 server block 處理 HTTPS 導向/非匹配請求。

盤點後 `https://ad.nghcc.org.tw/` 與 `http://127.0.0.1:26001/` 均回應 HTTP 200，公開端 TLS 驗證成功。正式程式目錄本身不是 Git working tree，因此部署版本不能由主機上的 commit hash 證明。
