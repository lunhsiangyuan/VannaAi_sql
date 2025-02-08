# VannaAI SQL Assistant

這是一個基於 VannaAI 的自然語言轉 SQL 查詢助手，能夠將使用者的自然語言問題轉換成 SQL 查詢語句。

## 功能特點

- 自然語言轉換 SQL 查詢
- RESTful API 支援
- 完整的錯誤處理和日誌記錄
- 支援直接 SQL 查詢和自然語言查詢
- 整合 OpenAI GPT-4 模型

## 系統需求

- Python 3.8+
- SQLite3
- OpenAI API Key

## 安裝步驟

1. Clone 專案：
```bash
git clone git@github.com:lunhsiangyuan/VannaAi_sql.git
cd VannaAi_sql
```

2. 建立虛擬環境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安裝依賴：
```bash
pip install -r requirements.txt
```

4. 設定環境變數：
建立 `.env` 檔案並加入以下設定：
```
OPENAI_API_KEY=your_api_key_here
FLASK_PORT=5000
```

## 使用方法

1. 啟動服務：
```bash
python app.py
```

2. API 端點：

### 自然語言查詢
- 端點：`/api/nl-query`
- 方法：POST
- 請求格式：
```json
{
    "question": "最近一週的銷售總額是多少？"
}
```

### 直接 SQL 查詢
- 端點：`/api/raw-sql`
- 方法：POST
- 請求格式：
```json
{
    "sql": "SELECT * FROM sales LIMIT 10;"
}
```

## 資料庫結構

### sales 表
- id: INTEGER PRIMARY KEY
- transaction_id: TEXT NOT NULL
- date: TEXT NOT NULL
- product_name: TEXT NOT NULL
- product_category: TEXT
- quantity: INTEGER
- unit_price: REAL
- total_amount: REAL

### transactions 表
- id: TEXT PRIMARY KEY
- created_at: TEXT NOT NULL
- status: TEXT NOT NULL

## 錯誤處理

系統會自動記錄所有錯誤到日誌檔案，包含：
- SQL 執行錯誤
- API 請求錯誤
- 系統錯誤

## 注意事項

- 請確保 OpenAI API Key 的有效性
- 資料庫檔案位置：`database/sales_data.db`
- 系統預設監聽所有網路介面 (0.0.0.0) 