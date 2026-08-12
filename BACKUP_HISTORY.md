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

## 2026-08-12 09:40:45 +08:00

- Purpose: integrate the complete recurring-booking fields and workflow into the main "新增場地登記" dialog while retaining the original recurring-booking entry point under room administration.
- GitHub commit: `49f8219` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-integration-20260812-094045/`.
- Deployed files: `modules/facility/views.py` and `templates/facility/booking_daily_overview.html`.
- Database, existing bookings, media, menu items, and permission relationships: unchanged.
- Verification: deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/facility/booking/` returned HTTP 200 and the recent container log contained no deployment error.

## 2026-08-12 10:31:05 +08:00

- Purpose: allow new recurring venue bookings to select multiple weekdays and multiple monthly week numbers, and allow cancelling only one occurrence or that occurrence and all following occurrences in the same series.
- GitHub commit: `8e30c84` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-series-20260812-103105/`.
- Deployed files: `modules/facility/views.py`, `templates/facility/booking_daily_overview.html`, and `templates/facility/rooms.html`.
- Database schema, existing bookings, media, menu items, and permission relationships: unchanged. Series identifiers apply only to newly created recurring bookings.
- Verification: deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/facility/booking/` and `/facility/rooms/` both returned HTTP 200; recent container logs contained no deployment error.

## 2026-08-12 10:55:44 +08:00

- Purpose: make the venue date picker navigate immediately, remove the redundant search and top-right new-booking buttons, and remove the legacy recurring-booking entry and modal from room administration.
- GitHub commit: `692950b` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-ui-20260812-105544/`.
- Deployed files: `templates/facility/booking_daily_overview.html` and `templates/facility/rooms.html`.
- Database schema, existing bookings, media, menu items, and permission relationships: unchanged.
- Verification: deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/facility/booking/` and `/facility/rooms/` both returned HTTP 200.

## 2026-08-12 11:47:26 +08:00

- Purpose: prevent single, recurring, and edited venue bookings from overlapping existing bookings, and show every conflict with its requested time, venue, existing activity, existing time, and registrant.
- GitHub commit: `4a46511` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-conflict-20260812-114622/`.
- Deployed files: `modules/facility/views.py` and `templates/facility/booking_daily_overview.html`.
- Database schema, existing bookings, media, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local files; 12 facility booking tests passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/facility/booking/` returned HTTP 200 and recent container logs contained no deployment error.

## 2026-08-12 16:37:30 +08:00

- Purpose: change the staff expense claim budget-code dropdown from usage percentage to activity and budget, while retaining code, ministry, and balance; the auto-debit claim dropdown remains unchanged.
- GitHub commit: `3486f05` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-budget-option-20260812-163656/`.
- Deployed files: `modules/facility/views.py` and `templates/facility/expense_claim.html`.
- Database schema, claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local files; 6 related tests passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-12 17:03:25 +08:00

- Purpose: allow long staff expense-claim budget descriptions to wrap and show the selected ministry, activity and budget, and balance on separate readable lines.
- GitHub commit: `4665a90` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-wrap-20260812-170258/`.
- Deployed file: `templates/facility/expense_claim.html`.
- Database schema, claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local file; 7 related tests passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.
