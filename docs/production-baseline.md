# 正式環境基線

> 2026-08-08：正式環境秘密已完成核心輪替，程式與 Compose 已改為環境變數。詳見 `security-rotation-20260808.md`。外部 NADS25 與 NU840 設備端限制另記於該紀錄。

基線日期：2026-08-05（Asia/Taipei）

## 執行基線

- 主機：`gino25` / `192.168.16.240`
- Compose project：`nads26`，兩個容器為 running。
- Web：`nads26-web`，image `nads26-web`，`26001:8000`。
- Database：`nads26db`，image `mysql:8.0`，實際 MySQL `8.0.43`，`33069:3306`。
- Network：`nads26_default`。
- Docker Engine：`28.5.1`；Docker Compose：`v2.40.1`。
- Nginx：`ad.nghcc.org.tw` HTTPS 反向代理至 `127.0.0.1:26001`。
- GitHub：`peterchen9/nghcc-nads26`，預設分支 `main`。

## 最新備份驗證

- 快照時間：2026-08-05 17:17:31（Asia/Taipei）。
- 遠端位置：`/home/apps1/nads26_backups/nads26_backup_20260805-171730`
- 本機位置：`D:\backups\nghcc-nads26\nads26_backup_20260805-171730`
- 本機總計：11,375,801,968 bytes，29 個檔案（含 manifest、config 與 inventory）。
- 25 筆 manifest checksum 在本機全部核對成功。
- 所有 tar/gzip 串流讀取成功。
- SQL dump：6,831,344 bytes，gzip 正常且 completion marker 為 1。
- media：archive/source 均為 41,899 files。
- static：archive/source 均為 34 files。
- application 490、legacy/log 2,806、MySQL live-copy 354、other-persistent 43 files，封包均可完整列舉。
- 既有 `/home/apps1/nads26/backups` 不嵌套進本次封包；先前遠端與本機完整備份另行保留。

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `archives/application.tar.gz` | 21,119,915 | `7a49a63507856a6f51d9fcddadc090aeb29ee816f2eb537cf9f8803f6f28bb31` |
| `archives/media.tar.gz` | 11,231,953,318 | `5b0c4c9492a3320b2b86e9ec55600fecae367b6fc1c4c8e08b1de21d8f9c5fcd` |
| `archives/static.tar.gz` | 30,991,596 | `f8c4e8ca06a3c019cc53d5f6d555c498643f265e61eca0f411e07fec0e664170` |
| `archives/other-persistent.tar.gz` | 20,352,714 | `e4a2578f3405bbb639cfe1b7f7e62fd8dabd8c29cc7f9b9246d7ba562ba41e14` |
| `archives/legacy-backups-and-logs.tar.gz` | 29,095,333 | `d4d98288cff22fac9e0e8e40e9a577ca65d9adb30e915a6fc537e83125f992e2` |
| `archives/mysql-data-live-copy.tar.gz` | 31,420,213 | `c6827c1fe5a7d95fb8163a142af2e5ceb75f56b8837922b077d5eb9030d78303` |
| `database/all-databases.sql.gz` | 6,831,344 | `3532dfbe174d54a131f368e49e82be3ab26fedc74802e985ff6809c57f8b0b6c` |

## 已知安全與維運風險

1. 備份期間因同時有 cron/rsync 活動，根分割區一度達 99%、可用約 23 GiB；工作結束後恢復為 86%、可用約 248 GiB。仍應確認該排程的暫存容量需求，並規劃容量監控與經核准的保存週期。
2. 受 Git 追蹤的 Compose 檔含兩個硬編碼 DB 密碼欄位；追蹤程式另有 Django `SECRET_KEY`、同步服務 password 與網路設備 password 的 literal 候選。此次不修改或輪替；後續應先確認引用面與有效性，再將秘密移至受控 secret store/`.env`，輪替憑證並評估清理 Git history。
3. MySQL port `33069` 綁定 `0.0.0.0` 與 IPv6 all interfaces；應確認防火牆與實際連線需求，能否改為 loopback 或限制來源須另案評估。
4. Web 以 Django development server (`manage.py runserver`) 執行；正式服務宜另案評估 production WSGI/ASGI server。
5. Web bind mount 整個正式程式樹，因此 `.env`、舊 dump、log、備份與資料檔都可能對容器可見；應另案縮小掛載範圍。
6. `nads26_nas_share` volume 的完整 inspect 可能含 NAS 連線資訊；不得提交或貼入公開紀錄。

以上只記錄發現，不代表已完成修正。
