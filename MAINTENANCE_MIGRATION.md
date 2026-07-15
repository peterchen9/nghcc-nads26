# 教會維護系統整合紀錄

## 2026-07-15 正式部署

- 目標系統：北門行政平台 NADS26（Docker，`192.168.16.240:26001`）
- 程式版本：`d9a971bcb560e155b4e05cb1ca8d6f5e03123dbd`
- 新增模組：維護儀表板、維護紀錄、廠商、分類、地點、費用統計、未完成追蹤、公開報修。
- 原有入口與功能保持不變；原「日常維護」頁僅新增「維護管理」入口。
- 資料庫遷移：`maintenance.0001_initial` 已套用。
- 匯入結果：分類 20、地點 24、廠商 19、維護紀錄 3、有效關聯附件 1。
- 來源另有 3 個未被現存紀錄引用的檔案，未任意掛入資料；已完整保留於來源快照。
- 匯入命令可重複執行，第二次驗證未建立重複資料或附件。

## 備份與驗證

- 資料移轉來源快照：`backups/maintenance-migration-20260715-170700`（本機，Git 忽略）
- 部署前完整備份：`backups/nads26-pre-maintenance-20260715-173653`（本機，Git 忽略）
- 伺服器備份：`/home/peterchen/backups/maintenance-migration-20260715-170700`
- 伺服器部署前備份：`/home/peterchen/backups/nads26-pre-maintenance-20260715-173653`
- SHA-256、SQL 完整結尾、壓縮檔清單均已驗證。
- Docker 測試：6 項全部通過；Django system check 僅保留原有 CKEditor 4 套件警告。
- 正式環境已驗證新舊路由、登入保護、公開報修頁、資料筆數與附件實體檔。

## 正式路由

- 原日常維護：`/facility/maintenance/`
- 維護管理：`/facility/maintenance/manage/`
- 公開報修：`/maintenance/report/`
