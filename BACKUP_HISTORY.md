# Backup History

## 2026-07-15 10:23:12 +08:00

- Source host: `192.168.16.240` (`gino25`)
- Source path: `/home/apps1/nads26`
- Local snapshot: `backups/nads26-full-20260715-102312/` (intentionally ignored by Git)
- Application files: complete tar/gzip archive excluding the live `mysql_data` directory
- Database: `nads26db`, exported with `mysqldump --single-transaction` including routines, triggers, events, and binary-safe values
- Source file count: 37,015
- Database dump size: 14,899,784 bytes
- Application archive size: 5,614,338,178 bytes
- `MANIFEST.txt` SHA-256: `fcf47c884fe08d35a33464a237621195a42950680dabae2cf09a08a72691ae3a`
- `nads26db.sql` SHA-256: `db29d59f4560ca6b3313340f806970fbcd880c7188a3776fd0b9ae86c64bd071`
- `nads26-files.tar.gz` SHA-256: `e7c8bd925c534ac7e395df9208e81049d4090a641828986e23e7c5439fcff6ed`
- Verification: remote and local SHA-256 checks passed; archive listing passed; SQL completion marker passed
- Runtime state during backup: `nads26-web` and `nads26db` remained running; no source data or directory structure was changed

## 2026-07-16 16:57:15 +08:00

- Purpose: restore the three existing finance routes for bank balances, fund/fellowship balances, and offering statistics.
- Remote backup: `/home/peterchen/backups/nads26-pre-finance-fix-20260716-165715/`
- Local backup: `backups/nads26-pre-finance-fix-20260716-165715/` (intentionally ignored by Git)
- Database: complete `nads26db` logical dump, 14,922,086 bytes.
- Database SHA-256: `d92fb7025ca2528327032db772d4b547fbe6d0b660891dbcc914fb8b4d967c27`
- Previous URL configuration SHA-256: `82e2a37267e541f985c683e5e71164d741b680a597623f125fe38e660cb8cd64`
- Verification: SQL completion marker and SHA-256 checks passed; deployment changed only three URL registrations and did not modify finance data.

## 2026-08-12 08:48:45 +08:00

- Purpose: add personal/marriage leave options, require a personal-leave explanation, correct the monthly-table AM/PM legend, and add leave-type help dialogs.
- GitHub commit: `ed09c19` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-leave-update-20260812-084845/`.
- Deployed files: `modules/staff/views.py` and `templates/staff/leaves.html`.
- Database, media, menu items, and permission relationships: unchanged.
- Verification: deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/staff/leaves/` returned the expected unauthenticated HTTP 302 response.

## 2026-08-12 09:20:01 +08:00

- Purpose: preserve sidebar, page, and nested content scroll positions after confirmed actions and form submissions.
- GitHub commit: `cdc3e4d` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-scroll-restore-20260812-092001/`.
- Deployed file: `templates/base.html`.
- Database, media, menu items, and permission relationships: unchanged.
- Verification: deployed SHA-256 `0ec3e78bc952d05addf10c84ae07721808f1487bb9cd389542131d71153d9853` matched the local file; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the home page returned HTTP 200 and `/staff/leaves/` returned the expected unauthenticated HTTP 302 response. A transient HTTP 502 occurred during the first second of container startup and cleared once Django was listening.
