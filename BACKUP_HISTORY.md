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

## 2026-08-13 10:45:27 +08:00

- Purpose: restore room photos in room administration and the room-detail gallery by serving existing uploaded room images through a safe Django endpoint instead of the unavailable collected-static path.
- GitHub commit: `b18ce46` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-room-photo-fix-20260813-104317/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-room-photo-fix-20260813-104317\` (outside the Git working tree).
- Deployed files: `modules/facility/views.py`, `modules/facility/urls.py`, and `modules/facility/tests_booking_day.py`.
- Database, room records, existing photo files, media, menu items, permission relationships, Nginx, and database container: unchanged.
- Verification: 14 related tests passed before deployment; deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/facility/rooms/`, `/facility/booking/`, and `/facility/room-photo/203.jpg/` returned HTTP 200; the photo response was `image/jpeg`; browser verification confirmed room-admin thumbnails had nonzero natural dimensions and the booking detail for room 203 loaded a 1920-by-1076 image.

## 2026-08-13 11:29:43 +08:00

- Purpose: restore hymn MIDI playback by serving the 2,907 existing MIDI files through an authenticated Django endpoint instead of the unavailable Nginx `/media/` path.
- GitHub commit: `7e53aac` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-midi-playback-fix-20260813-112546/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-midi-playback-fix-20260813-112546\` (outside the Git working tree).
- Deployed files: `modules/hymns/views.py`, `modules/hymns/serializers.py`, `modules/hymns/tests.py`, `nads26/urls.py`, and `templates/hymns/hymns_page.html`.
- Database, hymn records, MIDI files, media, menu items, permission relationships, Nginx, and database container: unchanged.
- Verification: 3 MIDI tests passed locally and on production; deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; the unauthenticated MIDI endpoint returned the expected HTTP 302; an authenticated browser playback request for `100801_時刻近主.mid` returned HTTP 200 with 2,321 bytes instead of the previous 404.

## 2026-08-13 11:44:59 +08:00

- Purpose: restore MIDI playback from the individual hymn detail dialog by returning a relative `midi_url`, preventing HTTPS pages from being blocked when Django incorrectly inferred the reverse-proxy request scheme as HTTP.
- GitHub commit: `776d251` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-midi-detail-url-fix-20260813-114234/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-midi-detail-url-fix-20260813-114234\` (outside the Git working tree).
- Deployed files: `modules/hymns/serializers.py` and `modules/hymns/tests.py`.
- Database, hymn records, MIDI files, media, menu items, permission relationships, Nginx, and database container: unchanged.
- Verification: 4 MIDI tests passed locally and on production; deployed SHA-256 values matched the local files; `python manage.py check` completed with only the pre-existing CKEditor 4 warning; `nads26-web` restarted successfully; `/` returned HTTP 200; the production detail API for hymn 1 now returns `/hymn_resources/midi/100801_%E6%99%82%E5%88%BB%E8%BF%91%E4%B8%BB.mid` instead of the blocked `http://` absolute URL.

## 2026-08-14 14:45:32 +08:00

- Purpose: calculate active staff annual leave from onboard dates, make the quota read-only, and add total/used/remaining annual-leave balances to the HR and personal leave summaries.
- GitHub publication: pending because the existing local `gh` authentication for `peterchen9` is invalid.
- Remote backup: `/home/peterchen/backups/nads26-pre-annual-leave-20260814-143931/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-annual-leave-20260814-143931\` (outside the Git working tree).
- Database change: applied `eureka.0011_staffinfo_annual_leave_opening_balance`; added three annual-leave tracking fields and loaded 18 existing staff opening balances for 2026-08-14, totaling 76 days. `施方正` was not created or matched because no corresponding `staff_info` record exists in production.
- Deployed files: `modules/eureka/models.py`, `modules/eureka/views.py`, `modules/eureka/test_staff_admin.py`, `modules/eureka/leave_rules.py`, `modules/eureka/migrations/0011_staffinfo_annual_leave_opening_balance.py`, `modules/eureka/test_leave_rules.py`, `modules/staff/views.py`, `modules/staff/tests.py`, `templates/eureka/staff_list.html`, and `templates/staff/leaves.html`.
- Unchanged: menu items, permission relationships, media, Nginx, and the database container configuration.
- Verification: 15 related tests passed locally; remote and local backup SHA-256 checks passed; all 10 deployed file hashes matched local files; Django check completed with the pre-existing CKEditor warning; migration `0011` is applied; opening-balance count and sum are 18 and 76; `nads26-web` restarted; `/` returned HTTP 200 and unauthenticated `/staff/leaves/` returned HTTP 302; authenticated browser verification confirmed the new summary order, correct `7 / 0 / 7` values for 陳潘傳, and a read-only annual-leave field in staff administration.

## 2026-08-14 15:02:03 +08:00

- Purpose: set the newly added staff record for 施方正 to the annual-leave opening balance supplied by the user.
- Remote backup: `/home/peterchen/backups/nads26-pre-fangzheng-leave-20260814-150203/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-fangzheng-leave-20260814-150203\` (outside the Git working tree).
- Database change: updated exactly one record, `staff_info.staff_id=26`, to a 2026 opening used-leave balance of 4 days with tracking starting on 2026-08-14. No other staff record was changed.
- Verification: the remote MySQL dump and local copy passed SHA-256 and gzip verification; the transaction updated exactly one row; the calculated balance is total 14, used 4, remaining 10; authenticated production browser verification showed `14 / 4 / 10` for 施方正 in the HR leave overview. No container restart was required.

## 2026-08-14 15:16:03 +08:00

- Purpose: move the HR-summary emphasis from the total annual-leave row to the monthly-total row, and present the personal total/used/remaining annual-leave cards in three distinct color tones on one three-column row.
- Remote backup: `/home/peterchen/backups/nads26-pre-leave-colors-20260814-151603/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-leave-colors-20260814-151603\` (outside the Git working tree).
- Deployed files: `templates/staff/leaves.html` and `modules/staff/tests.py`.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and database container configuration.
- Verification: 8 related tests passed locally; backup archives and local copies passed SHA-256 and tar verification; both deployed file hashes matched local files; Django check completed with the pre-existing CKEditor warning; `nads26-web` restarted; `/` returned HTTP 200 and unauthenticated `/staff/leaves/` returned HTTP 302. Authenticated production browser verification confirmed the monthly-total row background, normal total-annual-leave row background, three distinct blue/orange/green card tones, and a single three-column card row.

## 2026-08-14 15:53:30 +08:00

- Purpose: warn each staff member about expiring annual leave during the month before their onboard-anniversary month, including December warnings for January onboard dates.
- Remote backup: `/home/peterchen/backups/nads26-pre-leave-renewal-warning-20260814-155330/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-leave-renewal-warning-20260814-155330\` (outside the Git working tree).
- Deployed files: `modules/staff/views.py`, `modules/staff/tests.py`, and `templates/staff/leaves.html`.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and database container configuration.
- Verification: 10 related tests passed locally, including the January/December wraparound; remote and local backups passed SHA-256 and tar verification; all three deployed hashes matched local files; Django check completed with the pre-existing CKEditor warning; `nads26-web` restarted; `/` returned HTTP 200 and unauthenticated `/staff/leaves/` returned HTTP 302. Authenticated production browser verification used 陳潘傳's April onboard month: March showed the yellow background, red text, and renewal warning, while April returned to the normal green style.

## 2026-08-14 17:06:15 +08:00

- Purpose: limit the staff expense-claim history to each submitter by default, allow 黃美美 and superusers to switch between their own and all submissions, and replace the visible claim-number column with the claim-item purposes.
- GitHub publication: pending because the existing local `gh` authentication for `peterchen9` is invalid.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-claim-visibility-20260814-170152/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-expense-claim-visibility-20260814-170152\` (outside the Git working tree).
- Deployed files: `modules/facility/views.py` and `templates/facility/expense_claim.html`; the local test file was not deployed because tests are not retained in the production source tree.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and the database container configuration.
- Verification: 8 related tests passed locally; deployed SHA-256 values `1452f990ac66d5b0e90726b3abfa2efe5dbc99e9db6b304163bb73ca5ef8d7bb` and `404ec3238f0a4e4e267a70501413b40d75f9e04b68f2d89342567166200e4548` matched the local files; Django check completed with only the pre-existing CKEditor warning; 黃美美 has a linked login account; `nads26-web` restarted; the production root returned HTTP 200 and unauthenticated `/staff/expense-claims/` returned HTTP 302. Authenticated browser verification confirmed the superuser's own list contained only peterchen-created claims, the all-users list contained other applicants, and the table displayed purposes instead of claim numbers.

## 2026-08-16 09:09:28 +08:00

- Purpose: remove the `支票` payment method from the shared staff expense-claim and finance auto-debit claim form, leaving only bank transfer and cash.
- GitHub publication: pending because the existing local `gh` authentication for `peterchen9` is invalid.
- Remote backup: `/home/peterchen/backups/nads26-pre-remove-check-payment-20260816-090804/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-remove-check-payment-20260816-090804\` (outside the Git working tree).
- Deployed file: `templates/facility/expense_claim.html`.
- Unchanged: existing claim records, database schema, media, menu items, permission relationships, Nginx, and the database container configuration.
- Verification: 9 related tests passed locally; deployed SHA-256 `d559a4c426c625cbf5365985a6117f613ef0927b2c8820aa2ee7f9090f95f57b` matched the local file; the production container contains `匯款` and `現金` but no `支票` option; Django check completed with only the pre-existing CKEditor warning; `nads26-web` restarted; the production root returned HTTP 200, while unauthenticated staff-claim and auto-debit-claim pages both returned the expected HTTP 302.

## 2026-08-17 13:52:45 +08:00

- Purpose: correct 張慕聖's 2026 annual-leave opening used balance because the supplied 3-day value already included the scheduled half-day on August 28.
- Remote backup: `/home/peterchen/backups/nads26-pre-zhang-musheng-leave-fix-20260817-135034/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-zhang-musheng-leave-fix-20260817-135034\` (outside the Git working tree).
- Database change: updated exactly one record, `staff_info.staff_id=8` (`張慕聖`), changing `annual_leave_used_base` from 3.0 to 2.5 days. The tracking year remains 2026 and the tracking start remains 2026-08-14.
- Source consistency: corrected 張慕聖's value in the not-yet-published opening-balance migration from 3 to 2.5; the already-applied migration was not rerun in production.
- Verification: the production `staff_info` dump passed SHA-256 and gzip verification; the transaction checked the original values before updating; the calculated used annual leave is now 3.0 days after adding the scheduled 0.5 day on August 28; 10 staff-leave tests passed locally. No container restart was required.

## 2026-08-18 11:07:48 +08:00

- Purpose: prevent accidental modal dismissal when users click outside an editing dialog, using a shared base-template guard that covers leave, expense, staff, shift, facility, attendance, meeting, hymn, and other modal-backed pages while preserving explicit controls inside each dialog.
- GitHub publication: pending because the existing local `gh` authentication for `peterchen9` is invalid.
- Remote backup: `/home/peterchen/backups/nads26-pre-modal-backdrop-lock-20260818-110337/`.
- Local backups: `D:\backups\nghcc-nads26\nads26-pre-modal-backdrop-lock-20260818-105538\` for the pre-change local files and `D:\backups\nghcc-nads26\nads26-pre-modal-backdrop-lock-20260818-110337\` for the pre-deployment production file.
- Deployed file: `templates/base.html`.
- Local tooling compatibility: updated the local-only `.tools/ssh_exec.py` and `.tools/ssh_stream_extract.py` helpers to use a direct IPv4 socket when given a numeric address, working around the current bundled Python Unicode-DLL failure. These helper changes were not deployed.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and the database container configuration.
- Verification: deployed SHA-256 `4699fac633f0a490782e0c867118dbd77b9d14e575d8b03c8706488ec8d4df66` matched the local file; the production container contains the shared modal-backdrop guard; Django check completed with only the pre-existing CKEditor warning; `nads26-web` restarted; the production root returned HTTP 200 and unauthenticated `/staff/leaves/` returned HTTP 302. Automated Django tests could not start because the production application account cannot create `test_nads26db`, and browser click verification was unavailable because the Browser plugin rejected its updated runtime path as untrusted; neither failure touched production data.

## 2026-08-18 14:07:49 +08:00

- Purpose: redesign the staff expense-claim form and print layout, move ministry/group selection to each item using budget categories, and add login-specific reusable payee bank accounts.
- GitHub publication: pending; this deployment synchronized only the approved production files.
- Remote backup: `/home/peterchen/backups/nads26-pre-expense-claim-redesign-20260818-140513/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-expense-claim-redesign-20260818-140513\` (outside the Git working tree).
- Deployed files: `modules/facility/views.py` and `templates/facility/expense_claim.html`; the local test file and PDF layout sample were not deployed.
- Database change: added `ministry_group` to `facility_expense_claim_item`, preserving legacy claim-level values for existing rows, and created `facility_expense_payee_account` with per-login ownership and a unique owner/payee/account key. Existing claim and item counts remained 18 and 32; the new saved-account table started empty.
- Unchanged: existing claim amounts and approvals, menu items, permission relationships, media, Nginx, and database container configuration.
- Verification: remote and D-drive backup hashes matched; deployed hashes matched local files (`98e6d611...91479` and `bd501836...d53ce`); Django check completed with only the pre-existing CKEditor warning; schema initialization reported success; `nads26-web` restarted successfully; `/` returned HTTP 200 and unauthenticated `/staff/expense-claims/` returned HTTP 302.

## 2026-08-18 14:48:07 +08:00

- Purpose: make bank name, branch, and transfer account optional on expense claims, align the second-row fields by moving the `新增帳號` control below the transfer-account input, and prevent saving an empty reusable account.
- GitHub publication: pending; this deployment synchronized only the approved production files.
- Remote backup: `/home/peterchen/backups/nads26-pre-optional-bank-fields-20260818-144700/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-optional-bank-fields-20260818-144700\` (outside the Git working tree).
- Deployed files: `modules/facility/views.py` and `templates/facility/expense_claim.html`; the local test file was not deployed.
- Unchanged: database schema, existing claims and saved accounts, menu items, permission relationships, media, Nginx, and database container configuration.
- Verification: 13 related tests passed locally before deployment; remote and D-drive backup hashes matched; deployed hashes matched local files (`da08af07...8ec79` and `30ff837b...75114`); Django check completed with only the pre-existing CKEditor warning; the deployed template no longer makes bank fields required; `nads26-web` restarted successfully; claim/item/saved-account counts remained 19/33/1; `/` returned HTTP 200 and unauthenticated `/staff/expense-claims/` returned HTTP 302.

## 2026-08-21 10:06:23 +08:00

- Purpose: append `(請擇休)` to national-holiday names that fall on Sunday in the team leave table, and add `秋令會(同工禁休)` to 2026-10-03.
- GitHub commit: `d703d06` on `main`; this commit also published the previously deployed but uncommitted production-source updates from 2026-08-14 through 2026-08-18.
- Remote backup: `/home/peterchen/backups/nads26-pre-holiday-sunday-label-20260821-100512/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-holiday-sunday-label-20260821-100512\` (outside the Git working tree).
- Deployed file: `templates/staff/leaves.html`.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and database container configuration.
- Verification: the 30 tests covering staff, annual-leave rules/admin, and expense claims passed locally; the complete 60-test run had 58 passes and two pre-existing education CRUD failures caused by unexpected HTTP 403 responses; current-tree and all-reachable-history secret scans had no findings; remote and local backup SHA-256 values matched; deployed SHA-256 `dfa058d8c8cbf7173b162c65792da0cdec8c14be982a3ea7e1d71f9d496e158a` matched the local file; Django check completed with only the pre-existing CKEditor warning; `nads26-web` restarted successfully; `/` returned HTTP 200 and unauthenticated `/staff/leaves/` returned the expected HTTP 302.

## 2026-08-21 10:20:36 +08:00

- Purpose: show Sunday national-holiday compensatory-leave reminders and the October 3 autumn gathering notice consistently in both personal and team leave calendars, with long reminders split across clear lines.
- GitHub commit: `6ca6928` on `main`.
- Remote backup: `/home/peterchen/backups/nads26-pre-leave-notice-layout-20260821-101946/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-leave-notice-layout-20260821-101946\` (outside the Git working tree).
- Deployed file: `templates/staff/leaves.html`.
- Unchanged: database schema and records, media, menu items, permission relationships, Nginx, and database container configuration.
- Verification: all 10 staff-module tests passed locally; current-tree and all-reachable-history secret scans had no findings; remote and local backup SHA-256 values matched; deployed SHA-256 `289339ad9469ae97d8376c07c7bc6edb35c7d15eee5d4a8f94c6a02f9aa9c376` matched the local file; production markers for shared notices and both two-line layouts were present; Django check completed with only the pre-existing CKEditor warning; `nads26-web` restarted successfully; `/` returned HTTP 200 and unauthenticated `/staff/leaves/` returned the expected HTTP 302.

## 2026-08-21 10:45:38 +08:00

- Purpose: restore the three existing pastoral child menus under `牧者`, preserve the two `執事會` entries, and reconnect the existing backup app at `/backup/` for `管理員 → 資料備份`.
- GitHub commits: `a9ccb5d` restored the menu definitions, backup app source, and route; `43ad1ff` cleaned formatting in the restored source.
- Remote backup: `/home/peterchen/backups/nads26-pre-menu-restore-20260821-104317/`.
- Local backup: `D:\backups\nghcc-nads26\nads26-pre-menu-restore-20260821-104317\` (outside the Git working tree).
- Database change: updated only `parent_id` and `order` for existing `MenuItem` IDs 296, 307, and 308 in one transaction; no `MenuItem` was created, deleted, or rebuilt.
- Menu safety baseline: `MenuItem` count remained 49, permission relations remained 1,012, and non-superusers with zero menu permissions remained 0. Existing permission counts remained 19/20/20 for the three pastoral entries, 10/10 for the two deacon-board entries, and 8 for data backup.
- Deployed files: `nads26/urls.py` and `scripts/init_menu.py`; the backup app source already existed on production and was restored to Git for source consistency.
- Verification: all 11 menu and backup tests passed locally; Python AST and secret scans passed; the remote and D-drive backup manifest, SQL gzip/completion marker, and 1,969-file application archive passed verification; Django check completed with only the pre-existing CKEditor warning; `nads26-web` restarted successfully; `/` returned HTTP 200; unauthenticated `/backup/`, `/board/minutes/`, and `/facility/pastoral-reports/` returned the expected HTTP 302.
