# 備份與還原手冊

## 選單權限安全閘門

使用者權限以 `MenuItem` primary key 關聯。應用程式更新不得刪除後重建選單；選單同步必須原地更新既有資料，並保留未列於同步清單的自訂選單。

任何選單相關部署前後，都要以唯讀查詢記錄並比對：

- `MenuItem` 總數；
- `UserProfile.allowed_menu_items` 關聯總數；
- 沒有任何選單權限的非 superuser 人數。

部署前必須完成正常資料庫備份。若權限關聯數量非預期減少，立即停止，不得自動修復或繼續部署。

## 備份原則

1. 全程 `umask 077`，備份目錄只允許擁有者存取。
2. 不停止服務；MySQL 以 `mysqldump --single-transaction --quick` 建立一致性 logical dump，並包含 routines、events、triggers 與 binary-safe values。
3. 程式、media、static、其他持久化資料、legacy/log 與 MySQL live file copy 分開封包。既有完整備份目錄不再嵌套進新備份，以免重複占用空間；各代備份應各自保留與驗證。
4. `mysql-data-live-copy` 是執行中資料檔副本，可能不一致，只作次要災難復原參考；SQL dump 才是標準還原來源。
5. 保存 Docker/Compose/container/image/network/volume inspect、Nginx vhost、檔案清單、數量、大小與 SHA-256。
6. 遠端備份完成後複製到本機 `D:\backups\nghcc-nads26\` 的獨立日期時間目錄，不得先刪除任何來源。

## 建議備份目錄結構

```text
nads26_backup_YYYYmmdd-HHMMSS/
  BACKUP-INFO.txt
  SHA256SUMS
  archives/
  database/all-databases.sql.gz
  config/
  inventory/
```

`config/.env`、SQL、完整 inspect 與所有資料封包均屬敏感備份，不得提交 GitHub。

## 驗證

在遠端與本機分別執行：

```bash
sha256sum -c SHA256SUMS
gzip -t database/all-databases.sql.gz
tar -tzf archives/application.tar.gz >/dev/null
tar -tzf archives/media.tar.gz >/dev/null
tar -tzf archives/static.tar.gz >/dev/null
```

以 `tar -tzf ... | awk` 計算 media/static 檔案數，並與 `inventory/source-file-counts.txt` 核對。SQL 另檢查 mysqldump header、結尾 completion marker、database/table statements；不要在畫面輸出資料內容。

## 還原（需另行核准）

本文件只描述程序，不授權執行：

1. 先驗證 SHA-256 與封包可讀性，並建立現況備份。
2. 在隔離環境解開 application/media/static/other-persistent 封包。
3. 建立乾淨 MySQL 8.0 instance，解壓 SQL dump 後匯入。
4. 使用獨立 `.env` 注入秘密，禁止把正式密碼寫回 Git。
5. 完成 Django system check、資料抽查與 HTTP 驗證後，才規劃正式切換。

禁止直接將執行中取得的 `mysql-data-live-copy` 覆蓋正式 datadir；如 logical dump 無法使用，必須由 MySQL 管理者制定離線救援程序。
