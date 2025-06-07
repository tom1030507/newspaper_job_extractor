# 📰 報紙工作廣告區塊提取系統 (Newspaper Job Extractor)

<p align="center">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Ready" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/AI-Gemini%202.0-FF6F00?style=for-the-badge&logo=google&logoColor=white" alt="AI Gemini 2.0" />
  <img src="https://img.shields.io/badge/Flask-Web%20Framework-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License MIT" />
</p>

<p align="center">
  <strong>🚀 智能化的報紙工作廣告提取與分析系統</strong><br>
  使用 AI 技術自動從掃描報紙中提取工作廣告區塊，並進行結構化資料分析
</p>

<p align="center">
  <a href="https://newspaper-job-extractor-574680962945.asia-east1.run.app" target="_blank">
    <img src="https://img.shields.io/badge/🌐_線上體驗-立即使用-4CAF50?style=for-the-badge" alt="線上體驗" />
  </a>
</p>

---

## 🎯 專案概述

這是一個採用現代 Web 技術構建的智能報紙工作廣告提取系統，整合了 **OpenCV 圖像處理**、**Google Gemini AI** 和 **Flask Web 框架**。系統能夠自動從掃描的報紙圖像中識別並提取工作廣告區塊，並使用 AI 技術將其轉換為結構化資料。

### 🌟 核心特色

- 🔍 **智能區塊檢測**: 使用進階 OpenCV 算法精確識別工作廣告區塊
- 🤖 **AI 驅動分析**: 整合 Google Gemini 2.0 進行內容理解與結構化
- 🌐 **現代 Web 界面**: 響應式設計，支援即時進度追踪
- 🐳 **容器化部署**: 完整的 Docker 解決方案，支援生產環境
- 📊 **多格式輸出**: CSV、SQL、圖片等多種格式匯出
- ☁️ **雲端整合**: 一鍵同步至 Google Sheets

### 🏗️ 系統架構

```mermaid
graph TD
    A["👤 用戶"] --> B["🌐 Web 界面<br/>(Flask)"]
    B --> C["📁 文件上傳<br/>(PDF/JPG/PNG)"]
    C --> D["🔄 圖像預處理<br/>(OpenCV)"]
    D --> E["🔍 區塊檢測<br/>(輪廓分析)"]
    E --> F["🤖 AI 分析<br/>(Google Gemini)"]
    F --> G["📊 結構化資料<br/>(工作資訊)"]
    G --> H["💾 多格式輸出"]
    H --> I["📄 CSV"]
    H --> J["🗄️ SQL"]
    H --> K["🖼️ 圖片包"]
    H --> L["☁️ Google Sheets"]
    
    M["🐳 Docker 容器"] -.-> B
    N["🔑 Gemini API"] -.-> F
    O["📂 本地存儲"] -.-> G
    
    style A fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000
    style B fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style D fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style E fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    style F fill:#fff8e1,stroke:#f9a825,stroke-width:2px,color:#000
    style G fill:#e8f5e8,stroke:#388e3c,stroke-width:2px,color:#000
    style H fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000
    style I fill:#f1f8e9,stroke:#689f38,stroke-width:2px,color:#000
    style J fill:#f1f8e9,stroke:#689f38,stroke-width:2px,color:#000
    style K fill:#f1f8e9,stroke:#689f38,stroke-width:2px,color:#000
    style L fill:#f1f8e9,stroke:#689f38,stroke-width:2px,color:#000
    style M fill:#e0f2f1,stroke:#00796b,stroke-width:2px,color:#000
    style N fill:#fff3e0,stroke:#ff8f00,stroke-width:2px,color:#000
    style O fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#000
```

<div align="center">
  <em>🔄 數據流向：用戶上傳 → 圖像處理 → AI分析 → 結構化輸出</em>
</div>

---

## 🚀 快速開始

### 🌐 線上版本

**立即體驗，無需安裝**：
- 🔗 **線上網址**: [https://newspaper-job-extractor-574680962945.asia-east1.run.app](https://newspaper-job-extractor-574680962945.asia-east1.run.app)
- ⚡ **即開即用**: 無需下載或配置，直接在瀏覽器中使用

### 📋 本地部署需求

- **Docker**: 20.10+ 與 Docker Compose 1.29+
- **記憶體**: 最少 2GB，推薦 4GB
- **存儲**: 最少 5GB 可用空間
- **網絡**: Internet 連接（AI 功能需要）
- **API**: Google Gemini API 密鑰

### 🐳 Docker 部署（推薦）

1. **環境檢查**
   ```bash
   # Windows 用戶
   .\docker-check.bat
   
   # Linux/macOS 用戶
   docker --version && docker-compose --version
   ```

2. **一鍵部署**
   ```bash
   # Windows
   .\docker-start.bat
   
   # Linux/macOS
   chmod +x docker-start.sh && ./docker-start.sh
   ```

3. **驗證部署**
   - 🌐 主應用: http://localhost:8080
   - 🏥 健康檢查: http://localhost:8080/health

### 💻 本地開發環境

```bash
# 1. 克隆專案
git clone <repository-url>
cd newspaper_job_extractor

# 2. 安裝 Python 依賴
pip install -r requirements.txt

# 3. 環境配置
cp .env.example .env
# 編輯 .env 檔案，添加 Gemini API 密鑰

# 4. 啟動開發服務器
python app.py
```

### 🔑 API 密鑰設置

1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 創建新的 API 密鑰
3. 在系統首頁輸入 API 密鑰（會話期間有效）
4. 或在 `.env` 檔案中設置 `GEMINI_API_KEY`

---

## 🖼️ 處理效果展示

### 原始報紙 → 區塊提取
<div align="center">
  <img src="newspaper/newspaper1.jpg" alt="原始報紙" width="400" />
  <br><em>原始掃描報紙</em>
</div>

### 提取的工作廣告區塊
<div align="center" style="display: flex; gap: 10px; justify-content: center;">
  <img src="newspaper/newspaper1.jpg_blocks/239_954_927_1513.jpg" alt="工作區塊1" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/929_971_1615_1527.jpg" alt="工作區塊2" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/1618_2084_2284_2360.jpg" alt="工作區塊3" width="200" />
</div>
<div align="center"><em>自動提取的個別工作廣告</em></div>

### 處理步驟可視化
| 原始圖像 | 邊緣檢測 | 輪廓過濾 | 重建結果 |
|---------|---------|---------|---------|
| ![原始](newspaper/newspaper1.jpg_blocks/newspaper1_original.jpg) | ![邊緣](newspaper/newspaper1.jpg_blocks/newspaper1_mask_unprocessed.jpg) | ![輪廓](newspaper/newspaper1.jpg_blocks/newspaper1_mask_processed.jpg) | ![結果](newspaper/newspaper1.jpg_blocks/newspaper1_final_combined.jpg) |

---

## 📖 使用指南

### 1️⃣ 檔案上傳

**支援格式**:
- 📄 **PDF**: 多頁文件自動分頁處理
- 🖼️ **圖片**: JPG, PNG 格式
- 📁 **批量**: 最多 10 個檔案同時處理

**處理選項**:
- ✅ **自動校正方向**: AI 檢測並旋轉到正確方向
- ⚡ **並行處理**: 多線程加速 AI 分析

### 2️⃣ 處理進度

**進度階段**:
1. **上傳階段** (0-10%): 檔案接收與驗證
2. **處理階段** (10-60%): 圖像分析與區塊提取
3. **AI分析階段** (60-95%): 內容識別與結構化
4. **完成階段** (95-100%): 結果整理與儲存

### 3️⃣ 結果展示

**檢視功能**:
- 🔍 **圖片預覽**: 點擊放大檢視原圖
- 📝 **AI 分析**: 查看結構化提取資料
- 📊 **統計資訊**: 處理摘要與行業分布

---

## 📊 AI 分析結果

### 📋 資料結構

系統自動提取以下結構化資訊：

| 欄位 | 描述 | 範例 |
|------|------|------|
| **工作** | 職位名稱與職業類型 | 軟體工程師、行政助理 |
| **行業** | 19個標準行業分類 | 資訊科技業、金融業 |
| **時間** | 工作時間與班別 | 週一至週五 9:00-18:00 |
| **薪資** | 薪資待遇與福利 | 月薪 35,000-50,000 元 |
| **地點** | 工作地點與交通 | 台北市信義區、近捷運站 |
| **聯絡方式** | 電話、地址、Email | 02-1234-5678 |
| **其他** | 工作要求與備註 | 需具備英文能力 |

---

## 📥 匯出與整合

### 📄 下載格式

| 格式 | 描述 | 用途 |
|------|------|------|
| **CSV** | Excel 可開啟的表格檔 | 資料分析、製表 |
| **SQL** | 完整的資料庫語句 | 資料庫匯入 |
| **圖片** | 所有提取的區塊圖像 | 視覺化檢視 |
| **描述** | AI 分析的詳細文字 | 內容查看 |

### ☁️ Google Sheets 整合

**快速使用**:
1. 處理完成後點擊「創建 Google Sheets」
2. 系統自動創建新試算表並匯入資料
3. 自動設定共享權限，提供直接連結

**注意**: Google Sheets 整合功能需要配置 Google Apps Script URL

---

## 📚 文檔導覽

- 📖 **[詳細功能說明](docs/FEATURES.md)** - 完整功能特色與技術實現
- 🏗️ **[系統架構文檔](docs/ARCHITECTURE.md)** - 技術架構與設計說明
- ⚙️ **[配置與部署](docs/DEPLOYMENT.md)** - 進階配置與生產部署
- ❓ **[常見問題](docs/FAQ.md)** - 故障排除與最佳實踐

---

<div align="center">
  <p><strong>🎉 感謝使用報紙工作廣告區塊提取系統！</strong></p>
  <p>如果這個專案對您有幫助，請考慮給我們一個 ⭐ Star！</p>
</div>