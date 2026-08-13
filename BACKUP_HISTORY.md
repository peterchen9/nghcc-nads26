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

## 2026-08-12 17:16:06 +08:00

- Purpose: replace the native staff expense-claim budget selector with a custom multiline selector that wraps long code, ministry, activity and budget, and balance content, while preserving submitted budget codes and over-budget validation.
- GitHub commit: `86d2b0f` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-custom-picker-20260812-171538/`.
- Deployed file: `templates/facility/expense_claim.html`.
- Database schema, claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local file; 7 related tests and a JavaScript syntax check passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-13 08:52:22 +08:00

- Purpose: restore the native staff expense-claim budget dropdown, widen its column, reduce option text size, and keep budget details on one line for easier review.
- GitHub commit: `f058c86` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-native-picker-20260813-085150/`.
- Deployed file: `templates/facility/expense_claim.html`.
- Database schema, claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local file; 7 related tests and a JavaScript syntax check passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-13 09:17:41 +08:00

- Purpose: provide a wide, normal-size, wrapping staff expense-claim budget dropdown that opens above or below according to viewport space, retains only the selected budget code in the field, and shows the remaining details in smaller text below.
- GitHub commit: `91b2c79` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-wrapping-picker-20260813-091710/`.
- Deployed file: `templates/facility/expense_claim.html`.
- Database schema, claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local file; 7 related tests and a JavaScript syntax check passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-13 09:23:17 +08:00

- Purpose: create a confirmed milestone backup after acceptance of the staff expense-claim budget selector.
- GitHub baseline: `498d1a8c5b9cd568f6c8393c88dc62eb97c8b6cf` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-milestone-20260813-092316/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-milestone-20260813-092316\` (outside the Git working tree).
- Contents: application archive excluding live data and secrets, consistent `nads26db` logical dump, protected `.env`, Docker and requirements files, Nginx configuration, runtime inventory, and SHA-256 manifest.
- Backup size: 28,667,061 bytes across 11 files locally (about 28 MB on the remote host).
- Verification: all remote and local SHA-256 checks passed; the database gzip passed and contained the mysqldump completion marker; the application archive opened successfully and contained 516 files; protected configuration files were present; the running services were not stopped and production data was not modified.

## 2026-08-13 09:34:03 +08:00

- Purpose: remove the expense-claim item-name column, retain category, budget code, purpose, and amount, and widen the purpose field while preserving legacy storage compatibility.
- GitHub commit: `396b4f5` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-columns-20260813-093330/`.
- Deployed files: `modules/facility/views.py` and `templates/facility/expense_claim.html`.
- Database schema, existing claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: uploaded and deployed SHA-256 values matched the local files; 9 related tests and a JavaScript syntax check passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated `/staff/expense-claims/` check returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-13 09:42:11 +08:00

- Purpose: apply the staff expense-claim budget selector design to the finance auto-debit claim, including activity-and-budget details instead of usage percentage.
- GitHub commit: `0ae51bc` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-auto-debit-design-20260813-094143/`.
- Deployed file: `modules/facility/views.py`; the already deployed shared `templates/facility/expense_claim.html` remained unchanged.
- Database schema, existing claim records, budget records, menu items, and permission relationships: unchanged.
- Verification: the uploaded and deployed SHA-256 value matched the local file; 10 related tests passed before deployment; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; unauthenticated checks for `/finance/auto-debit-claims/` and `/staff/expense-claims/` both returned the expected HTTP 302 and recent container logs contained no deployment error.

## 2026-08-13 10:27:10 +08:00

- Purpose: show the national-holiday name beside the date in the personal leave calendar and on the second line beneath the date in the team monthly leave table.
- GitHub commit: `d94c77b` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-holiday-labels-20260813-101750/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-holiday-labels-20260813-101750\` (outside the Git working tree).
- Deployed files: `templates/staff/leaves.html` and `modules/staff/tests.py`.
- Database, leave records, media, menu items, permission relationships, Nginx, and database container: unchanged.
- Verification: 7 related tests passed before deployment; deployed SHA-256 values `e89aebdbea9829a426820c357530d86b51dcffe04f16eb5d1bc3e48658866574` and `fe483ea612e6bef493827b0ced8fb60357f7730d43f01d02e02cbf9cbd236428` matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/` returned HTTP 200 and the unauthenticated `/staff/leaves/` check returned the expected HTTP 302.
