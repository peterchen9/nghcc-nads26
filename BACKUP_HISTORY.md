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

## 2026-07-21 14:00:29 +08:00

- Purpose: add a read-only daily overview to the existing facility booking page.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-day-20260721-140029/`
- Local backup: `backups/nads26-pre-booking-day-20260721-140029/` (intentionally ignored by Git)
- Backup scope: the existing facility booking view, URL configuration, and booking template; no database schema or booking data was changed.
- Code archive SHA-256: `da9b33abc235c2dfeb97ecbb8f4a202a5b03a038d9c2a9cff325aed140a5839e`
- Feature commit: `da30d32`.
- Verification: three isolated Docker tests passed; the production daily overview, existing booking page, and room page returned HTTP 200; browser date switching and console checks passed.

## 2026-07-21 16:04:51 +08:00

- Purpose: reorder facility booking floors to `1F/2F/3F/4F/5F/6F/B1F/其他` and compact the daily overview into vertical one-character-wide room columns.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-order-20260721-141928/`.
- Local backup: `backups/nads26-pre-booking-order-20260721-141928/` (intentionally ignored by Git).
- Remote code archive SHA-256: `0053609594165392a9402dabbf8933f7a1e60bca2393bf44eb04368cf7e5aaa5`.
- Local pre-change archive SHA-256: `344c49a065e1164b6be3a544062671b7c8f0caebe971c58aa1217fd1fbe4bfe8`.
- Feature commit: `c33c81cf`.
- Deployment scope: `modules/facility/views.py` and `templates/facility/booking_daily_overview.html`; no database, booking data, Docker volume, or unrelated feature was changed.
- Verification: four isolated Docker tests and Django checks passed; production booking, daily overview, and room pages returned HTTP 200 from the host; browser checks confirmed both booking floor lists, all eight daily overview floor groups, 36 compact vertical room columns, and no console errors.

## 2026-07-21 17:27:20 +08:00

- Purpose: make the facility daily overview interactive while preserving the existing booking workflow and permissions.
- Feature branch: `codex/facility-daily-booking`.
- Remote backup: `/home/peterchen/backups/nads26-pre-daily-interactive-20260721-172045/`.
- Local backup: `backups/nads26-pre-daily-interactive-20260721-172045/` (intentionally ignored by Git).
- Remote pre-change archive SHA-256: `126711a637fe008ee1c0c847fd5e846ad80337e1e72dc1cb18873864bca58575`.
- Local pre-change archive SHA-256: `43ebe7e3895084d2b4f50a37bb096aa522f70edd809c4febcd3ba6298d6de9dc`.
- Deployment archive SHA-256: `02c794581f9be1b24f62d532bab089d88dca36f7fa0f4d69029769489ab21b77`.
- Feature commit: `cbedcfb`.
- Deployment scope: `modules/facility/views.py` and `templates/facility/booking_daily_overview.html`; no database schema, booking data, Docker volume, or unrelated feature was changed.
- Verification: six isolated Docker tests and Django checks passed; browser tests opened a prefilled new-booking form, a permission-aware existing-booking view, and an actual room image without submitting any form; the original eight bookings remained unchanged and no browser console errors were reported.

## 2026-07-22 17:31:56 +08:00

- Purpose: remove the visible room-map label and normalize all daily-overview time cells while retaining every interaction.
- Remote backup: `/home/peterchen/backups/nads26-pre-daily-cell-fix-20260722-172029/`.
- Local backup: `backups/nads26-pre-daily-cell-fix-20260722-172029/` (intentionally ignored by Git).
- Remote pre-change archive SHA-256: `139a202fdb7a04ebbc69f430b3b91d3929f8b4021208f3f94a71febee5bcb67b`.
- Local pre-change archive SHA-256: `5dd2ba6f388d9ad592f7fb01292ff5729b48dbc58532ab43f9fefcea97d755cb`.
- Final deployment archive SHA-256: `18c1e0366cee1e195c16ad443f40aa022af0ec7a476281e455b0c0996301e90b`.
- Feature commit: `82115ac1`.
- Deployment scope: `templates/facility/booking_daily_overview.html` only; tests were updated locally, and no database schema, booking data, Docker volume, or unrelated feature was changed.
- Verification: six isolated Docker tests and Django checks passed; production browser checks confirmed no visible map labels, no booking rowspans, equal empty/booked row heights, working new-booking/existing-booking/room-map dialogs, and no console errors. No form was submitted.

## 2026-07-22 17:59:10 +08:00

- Purpose: use the interactive all-room overview as the single facility-booking entry while preserving the previous dual-view design.
- Preserved GitHub branch: `codex/facility-booking-dual-view-archive-20260722` at commit `3a15fbb2`.
- Remote backup: `/home/peterchen/backups/nads26-pre-booking-single-entry-20260722-175452/`.
- Local backup: `backups/nads26-pre-booking-single-entry-20260722-175452/` (intentionally ignored by Git).
- Remote dual-view archive SHA-256: `44ba55845f4013d6f714059cd27d59a42319cbc6976e03becad27a38a28ad4fb`.
- Local dual-view archive SHA-256: `deb3ff3a6ba510fa2aa4c5944247728c98720e2ae7b69647cba7214d19806bdb`.
- Deployment archive SHA-256: `7be19eb4645ca4231d3525279fd366edd30f2adc6ac650cf9eed2972329ef452`.
- Feature commit: `38ff948`.
- Deployment scope: `modules/facility/views.py` and `templates/facility/booking_daily_overview.html`; the previous `templates/facility/booking.html` remains intact, and no database schema, booking data, Docker volume, or unrelated feature was changed.
- Verification: six isolated Docker tests and Django checks passed; production checks confirmed `/facility/booking/` renders the interactive overview, the old `/facility/booking/day/` URL redirects with its date intact, booking and room-image dialogs work, and no console errors were reported. No form was submitted.
