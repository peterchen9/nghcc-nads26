# 北門行政平台模組化盤點（第一版）

盤點日期：2026-08-18（Asia/Taipei）

## 長期方向與目前決議

- 長期目標：把所有功能拆成可選用、可組合的「樂高式模組」，在同一平台底座上依需求組成不同版本的完整系統。
- 模組化範圍必須包含程式、資料表、URL、選單、權限、主資料、外部整合與版本依賴，不能只隱藏選單。
- 目前決議：暫緩實際拆分與模組註冊中心開發，優先把現有平台功能建置完整、資料與流程穩定。
- 未來啟動條件：平台主要功能完成後，回到本文件重新確認主資料邊界、模組依賴及第一個拆分模組，再分階段執行。
- 建議第一個標準範本：請款模組；其後依序評估場地、維修與巡檢模組。

## 1. 本次目標與範圍

本文件將現行平台同時用兩個維度整理：

1. **使用者功能維度**：依左側功能列規劃「大分類／小功能」。
2. **整合資料維度**：建立員工、會友、廠商、場地、設備、固定資產、浮動資產七類共用主資料。

第一階段只做盤點與目標架構，不直接更名 Django app、不搬資料表、不改正式選單與權限。

## 2. 現況摘要

- 正式環境目前有 49 筆啟用選單資料，採兩層 `MenuItem.parent` 結構。
- 現行主要程式 app：`accounts`、`menu`、`pages`、`eureka`、`staff`、`facility`、`maintenance`、`budget`、`education`、`file_center`、`hymns`、`humnos`、`power`、`network`。
- 正式資料庫同時包含 Django ORM 資料表、外部匯入資料表，以及由 view 執行期間建立的原始 SQL 資料表。
- 選單名稱、URL 前綴、Django app 與資料表前綴目前不是一對一關係。
- `facility/views.py` 同時包含場地、牧養報告、維修、請款、教室巡檢與 network 轉接，是目前最大的模組邊界問題。

## 3. 建議左側功能列（大分類／小功能）

左側選單先維持兩層，避免立即修改權限模型。第一版建議如下：

| 大分類 | 小功能 | 現行來源 | 建議模組代號 |
| --- | --- | --- | --- |
| 人員 | 員工資料、休假、出勤、排班、座位、行事曆 | `eureka`、`staff` | `people.staff`、`hr.*` |
| 人員 | 會友查詢、新朋友、牧區小組、名單整理 | `eureka` | `people.member`、`care.groups` |
| 事工 | 牧養報告 | `facility` | `care.reports` |
| 事工 | 詩歌、洗禮、聖餐、婚禮、安息禮 | `hymns`、`pages` | `ministry.worship.*` |
| 事工 | 課程規劃與課堂資料 | `education` | `ministry.education` |
| 行政 | 場地預約、每日總覽 | `facility` + 外部 MRBS | `operations.booking` |
| 行政 | 請款單、自動扣繳單 | `facility`、`staff`、`budget` | `operations.expense` |
| 場地資產 | 場地資料、教室巡檢 | `facility` | `assets.location`、`operations.inspection` |
| 場地資產 | 設備、日常維修、定期保養 | `facility`、`maintenance` | `assets.equipment`、`operations.maintenance` |
| 場地資產 | 固定資產 | 尚未建立 | `assets.fixed` |
| 場地資產 | 浮動資產 | 尚未建立 | `assets.current` |
| 財會 | 預算、銀行、基金、團契款、奉獻統計 | `budget` | `finance.*` |
| 文件資訊 | 檔案中心、媒體、網路影音 | `file_center`、`pages`、`humnos` | `content.*` |
| 資訊設備 | LAN、WLAN、用電監測 | `network`、`power`、`facility` | `it.network`、`it.power` |
| 系統管理 | 使用者、權限、選單、備份、系統設定 | `accounts`、`menu`、外部 backup app | `core.*` |

### 選單原則

- 大分類只負責導覽，不直接代表資料擁有權。
- 每個小功能對應一個可獨立啟用的功能模組。
- 權限繼續綁定小功能的既有 `MenuItem` primary key；未來調整父分類時不可刪除重建選單。
- 同一個主資料可被多個功能引用，例如「廠商」同時供維修與請款使用，但只保留一份權威主檔。

## 4. 七類整合主資料

| 主資料類別 | 現有資料來源 | 完整度 | 主要問題 | 第一版目標 |
| --- | --- | --- | --- | --- |
| 員工 | `staff_info`、`auth_user`、`accounts_userprofile` | 中 | 登入帳號、員工資料與會友身分未統一；出勤、休假仍有姓名或帳號字串關聯 | 建立穩定 `staff_id` 與帳號關聯；其他表逐步改用員工 FK |
| 會友 | `members`、牧區／小組表 | 中高 | `members` 為 `managed=False` 外部主檔；員工若也是會友，沒有正式身分關聯 | 保留外部 church ID，新增平台內部 person/party 對應層 |
| 廠商 | `maintenance_maintenancevendor`、`facility_expense_payee_account` | 低至中 | 維修廠商與個人常用收款帳號分離，可能重複姓名與銀行資料 | 建立共用 Vendor/Payee 主檔；個人常用帳號改為偏好／捷徑，不作第二主檔 |
| 場地 | 外部 MRBS、`maintenance_maintenancelocation`、巡檢 room 表、照片檔名 | 低 | 同一場地以多套名稱／ID 存在，教育課程也直接讀 facility room helper | 建立 Location 主檔與 MRBS 外部 ID 對照；巡檢、維修、課程全部引用 Location |
| 設備 | 定期保養項目、維修紀錄文字、網路主機 | 低 | 沒有獨立設備編號、類型、所在位置、責任人、狀態與生命週期 | 建立 Equipment 主檔；保養與維修紀錄改引用設備 FK |
| 固定資產 | 尚無完整資料表 | 無 | 無資產編號、取得日期、成本、折舊、保管人與報廢流程 | 新建 FixedAsset，可選擇連結 Equipment、Location、Vendor |
| 浮動資產 | 銀行帳戶、基金、定存、團契餘額等財務資料；尚無一般物資主檔 | 部分 | 現有資料偏財務餘額，尚未定義現金、存貨、耗材或短期資產邊界 | 先定義範圍；財務資產與物資存量分成子類，不直接混用同一張表 |

## 5. 建議程式目錄

```text
nads26/
  core/
    identity/          # 登入帳號、角色、權限
    navigation/        # 動態選單與模組註冊
    audit/             # 共用操作紀錄
    files/             # 共用附件與檔案服務
  master_data/
    people/            # person、員工、會友身分對照
    vendors/           # 廠商、收款人、銀行帳號
    locations/         # 場地、區域、樓層、外部 MRBS 對照
    equipment/         # 設備主檔
    assets/            # 固定資產、浮動資產
  domains/
    hr/                # 休假、出勤、排班、行事曆
    care/              # 牧區、小組、牧養報告
    worship/           # 詩歌、洗禮、婚禮、安息禮
    booking/           # 場地預約
    inspection/        # 場地／設備巡檢
    maintenance/       # 維修、保養
    expense/           # 請款、自動扣繳、傳票
    finance/           # 預算、銀行、基金、奉獻
    education/         # 課程與課堂
    content/           # CMS、媒體、檔案中心
    it_ops/            # LAN、WLAN、用電
  integrations/
    mrbs/              # 場地預約外部 DB
    attendance/        # 打卡／出席匯入
    nas/               # NAS 與媒體
    legacy_members/    # 會友外部主檔同步
```

這是目標目錄，不應一次搬完。第一階段可以保留現有 URL，透過相容轉接逐步移動服務。

## 6. 建議的可重組模組單位

每個可安裝模組應有同一種結構：

```text
module_name/
  apps.py
  models.py
  services.py
  selectors.py
  urls.py
  permissions.py
  menu.py
  migrations/
  templates/module_name/
  tests/
```

並提供一份模組描述資料：

- 模組代號與版本。
- 依賴的其他模組。
- 提供的 URL 與選單項目。
- 提供／使用的權限。
- 擁有的資料表與使用的共用主資料。
- 可選的外部整合與必要環境變數。

如此才能依需求組合，例如：

- **基本行政版**：core + 員工 + HR + 場地預約 + 請款。
- **教會牧養版**：core + 會友 + 牧區小組 + 牧養報告 + 崇拜禮儀。
- **資產維運版**：core + 場地 + 設備 + 巡檢 + 維修 + 固定資產。
- **完整版**：所有模組與整合介面。

## 7. 目前主要耦合與風險

### 高優先

1. `facility/views.py` 擁有多個不相關領域，且直接建立原始 SQL 資料表。
2. `staff` 與 `budget` 直接匯入 `facility` 的請款 view，依賴方向顛倒。
3. `facility` 直接匯入 `network` view；URL 外觀仍是 `/facility/lan-hosts/`。
4. `education` 直接使用 `facility` 的私有 `_rooms`、`_room_by_id` helper。
5. 員工、會友、登入使用者以不同 ID 或姓名字串互相對應，資料一致性風險高。

### 中優先

1. 場地存在 MRBS、維修地點、巡檢房間與照片檔名四套識別方式。
2. 廠商銀行資料與個人請款常用帳號可能形成重複資料。
3. `facility`、`staff` 多張資料表由頁面執行時 `CREATE TABLE`，缺少正式 migration 邊界。
4. 選單初始化腳本與正式資料庫可能不同步；正式已有空父選單與額外備份功能。
5. 現有 MenuItem 僅兩層；如果要第三層，必須先設計權限與 UI 相容方案。

## 8. 建議拆分順序

### 階段 0：規格固定（不搬資料）

- 確認本文件的大分類、小功能與七類主資料命名。
- 為現有功能建立「模組代號 → URL → 選單 ID → 資料表」清單。
- 為跨模組功能建立回歸測試與資料筆數基線。

### 階段 1：建立共用主資料層

- 先做 `Location`、`Vendor`、`Equipment`，因目前缺口與重複最明顯。
- 建立外部 ID 對照表，不直接改掉 MRBS 或 members 的既有 primary key。
- 以 nullable FK 漸進導入，保留舊欄位供比對與回復。

### 階段 2：拆 `facility`

- 先抽出 `expense`，因已有 staff、finance 兩個入口與清楚的 claim type。
- 再抽 `care.reports`、`inspection`、`maintenance_legacy`。
- 最後把 network 路由歸還 `it_ops`，booking 歸入獨立 booking integration。

### 階段 3：整理人員身分

- 建立 Person/Party 對照層，連結 `auth_user`、`staff_info`、`members`。
- 出勤、休假、請款建立者逐步改用穩定 FK，不再只靠姓名或 username。

### 階段 4：建立資產模組與模組開關

- 補齊固定資產、浮動資產資料模型。
- 導入 module registry，由設定決定安裝 app、URL、選單與權限。
- 保留既有 MenuItem ID，僅更新父分類與排序。

## 9. 第一版驗收標準

在真正搬動第一個模組前，至少應具備：

- 每個現有選單路由都有對應模組代號。
- 每張業務資料表有唯一資料擁有模組。
- 七類主資料各有明確權威來源與 ID 策略。
- 所有跨模組 import 都被列入替換清單。
- 可在不刪除 MenuItem 的前提下重新分類左側選單。
- 正式資料表筆數、權限關聯與零權限一般使用者數有部署前後核對機制。

## 10. 下一次整理建議

第二版先聚焦三個決策：

1. 「人員」是否採用共用 Person，再掛員工／會友兩種身分。
2. 「浮動資產」的業務範圍，是只含財務流動資產，還是也包含耗材與可移動物品。
3. 第一個實際拆分模組選擇 `expense` 或共用 `locations`。

決策完成後，再產出實際資料模型 ERD、模組依賴圖與分階段 migration 計畫。
