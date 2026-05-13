---
name: TXF-Pipeline CI/CD Define
description: 依據現行開發模式與微服務架構，所定義之 CI/CD 最佳實踐藍圖。供後續建立部署流程或新增相關 Action 時參照用。
---

# TXF-Pipeline CI/CD 導入指南

基於目前的架構（純 Python 加上 Docker Compose 容器化微服務），本專案適合導入現代化的 CI/CD 流程。以下是專為這個架構量身打造的 CI/CD 最佳實踐藍圖。

## 1. 架構概述：從開發到正式上線

目前的專案依賴 `docker-compose up --build` 進行更新，這在開發環境中非常方便。但到了正式上線的環境，我們通常遵循 **「Build Once, Run Anywhere (建置一次，到處執行)」** 的準則。

未來的部署藍圖應該長這樣：
1. **GitHub/GitLab (原始碼)** 👉 2. **CI Server (建置/測試)** 👉 3. **Image Registry (存放 Docker Image)** 👉 4. **Production 伺服器 (下載並重啟)**

---

## 2. CI (Continuous Integration): 持續整合

當推送程式碼（Push 到 main 或建立 Pull Request）時，自動執行以下驗證：

### 階段一：靜態程式碼檢查與測試 (Test)
*   **Linting & Formatting**：使用 `Ruff` 或 `Flake8` 確保程式碼風格一致且無語法錯誤。確保嚴謹的 API 設計，這能避免基本的 typo 排錯。
*   **Unit Tests**：使用 `pytest`。幫 OHLC 轉換與 API 返回值的解析邏輯寫單元測試。

### 階段二：Docker 映像檔建置 (Build)
*   自動使用目前的 `docker/python/Dockerfile` 建置映像檔。這個步驟是為了保證所有的 `requirements.txt` 都是可以順利安裝的。

---

## 3. CD (Continuous Deployment): 持續部署

當 `main` 分支有新版發佈（例如打上 Tag `v1.2.0`），就會觸發 CD 流程自動將服務更新。

### 階段一：上傳映像檔 (Push to Registry)
自動將剛剛編譯好的 Image 推送到 Registry 中。
*   **免費選項**：GitHub Container Registry (GHCR)、Docker Hub、GitLab Container Registry。
*   我們會將您的 Image 命名為：`ghcr.io/your_username/txf-pipeline:latest`。

### 階段二：正式機部署 (Deploy)
*   **無需重編譯**：在正式機上，**不要**執行 `docker-compose build`。
*   CI 工具會透過 SSH 遠端連入正式機，並下達指令：
    ```bash
    docker-compose pull   # 拉取剛建置好的最新 Image
    docker-compose up -d  # 無縫重啟有更新的微服務容器
    ```

---

## 4. GitHub Actions 實作範例

這是一份為專案設計的 CI/CD `workflow.yml` 範例參考（放置於 `.github/workflows/deploy.yml`）：

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ "main" ]

jobs:
  build_and_push:
    runs-on: ubuntu-latest
    steps:
      - name: 📥 Checkout Code
        uses: actions/checkout@v3

      - name: 🐳 登入 GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: 🔨 建置與上傳 Docker Image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./docker/python/Dockerfile
          push: true
          tags: ghcr.io/your-username/txf-pipeline-base:latest

  deploy:
    needs: build_and_push
    runs-on: ubuntu-latest
    steps:
      - name: 🚀 部署至正式伺服器
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /opt/txf-pipeline
            # 將 docker-compose.yml 內的 build: . 移除或替換成 image: ghcr.io/...
            docker-compose pull
            docker-compose up -d
```

---

## 5. 專案需要調整的地方

為了符合 CI/CD 的準則，您的專案會需要做一點小調整：

1. **Docker Compose 切分**：
   準備兩份設定檔：
   *   `docker-compose.yml` 或 `docker-compose.override.yml`：用於本地開發（直接掛載 `./src:/app/src`、使用 `build:` 指令）。
   *   `docker-compose.prod.yml`：用於正式機部署（移除 volume 掛載 `src`、改用設定好的 `image: ghcr.io/...`）。

2. **機密資料保護 (Secrets)**：
   目前您的 `docker-compose.yml` 依賴 `.env` 來填入 `SHIOAJI_API_KEY` 與 `INFLUXDB_INIT_ADMIN_TOKEN`。這些資料絕對不能進版控。
   *   在 CI/CD 設定中（如 GitHub Secrets），只存放 `SERVER_HOST`、`SERVER_SSH_KEY` 等部署機密。
   *   實際的 `.env` 檔案應透過手動建立在部署的主機上並持久保留，不從 CI/CD 管線中拉取，這樣最安全。
