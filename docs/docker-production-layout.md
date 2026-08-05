# Docker 正式環境配置

## 執行拓樸

```text
Internet / LAN client
        |
        v
Nginx :443 (ad.nghcc.org.tw)
        |
        v
127.0.0.1:26001 -> nads26-web:8000
                         |
                         | nads26_default
                         v
                    nads26db:3306
                         |
                         v
/home/apps1/nads26/mysql_data
```

`nads26-web` 使用 `/home/apps1/nads26:/app` bind mount，因此正式執行內容直接取自主機程式目錄。DB 使用同一來源樹下的 `mysql_data` bind mount。

## 已確認的 Docker/Compose 定位依據

- `docker compose ls --all`：專案 `nads26` 的 config file 為 `/home/apps1/nads26/docker-compose.yml`。
- 容器 label `com.docker.compose.project.working_dir`：`/home/apps1/nads26`。
- 容器 label `com.docker.compose.project.config_files`：`/home/apps1/nads26/docker-compose.yml`。
- 兩個容器的 Compose project label：`nads26`。

## 操作邊界

日常盤點可使用 `docker compose ls`、`docker ps` 與選欄位的 `docker inspect`。完整 `docker inspect` 可能包含環境秘密，只能存入受限制備份，不可貼入 issue 或 commit。

任何 `compose up/down/restart/build`、容器修改、volume 權限調整或 Nginx reload 都是變更作業，須另立維護窗口與核准。
