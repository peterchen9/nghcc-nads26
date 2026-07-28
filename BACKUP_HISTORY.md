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

## 2026-07-28 17:35:05 +08:00

- Source host: `192.168.16.240`
- Source path: `/home/apps1/nads26`
- Remote snapshot: `/home/peterchen/backups/nads26-full-20260728-173505/`
- Local snapshot: `backups/nads26-full-20260728-173505/` (intentionally ignored by Git)
- Application files: complete tar/gzip archive including uploaded media, excluding the live `mysql_data` directory and nested backups
- Database: `nads26db`, exported with `mysqldump --single-transaction` including routines, triggers, events, and binary-safe values
- Source file count: 36,988
- Database dump size: 15,079,352 bytes
- Application archive size: 6,510,538,283 bytes
- GitHub-safe code archive size: 32,153,231 bytes
- `MANIFEST.txt` SHA-256: `dd08dbfd8ccb3e521f5815cadd862b32fab1608d40e70fcb44b9bcdb6361f110`
- `nads26db.sql` SHA-256: `6ec1e4fcedf88fb63093a7f3d7bcd0d6fe140eb317e96d3419c89c2adae5e507`
- `nads26-files.tar.gz` SHA-256: `872be956ff7397debd8574c6267e0a534d9c5f6e570568e9330734c13f68e87f`
- `nads26-github-code.tar.gz` SHA-256: `dc55335537a6a419ab14403dc6d4b4b4f125890bf2f023c84f884cbc4e5a6192`
- Verification: remote and local SHA-256 checks passed; both archive listings passed remotely and locally; SQL completion marker passed
- Runtime state during backup: `nads26-web` and `nads26db` remained running; HTTP health check returned `200`; Django system check completed with the existing CKEditor 4 support warning only
- GitHub safety: database dumps, uploaded media, local secrets, logs, archives, and the backup payload are excluded from the public repository
