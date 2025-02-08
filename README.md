# Square SQL 自然語言查詢助手

這是一個基於 Flask 和 OpenAI 的應用程式，能夠將自然語言轉換為 SQL 查詢，並提供直觀的介面來分析 Square 銷售數據。

## 功能特點

- 🤖 自然語言轉 SQL：使用 OpenAI GPT-4 將中文問題轉換為精確的 SQL 查詢
- 📊 銷售數據分析：完整的 Square 銷售數據分析功能
- 🛡️ SQL 驗證：內建 SQL 驗證機制，確保查詢安全性
- 📝 詳細日誌：完整的日誌記錄，方便除錯和監控
- 🔄 API 端點：提供 REST API 介面
- 💡 智能訓練：支援自定義業務術語和範例查詢訓練

## 專案結構

```
.
├── app.py                  # 主要應用程式
├── sql_validator.py        # SQL 驗證工具
├── templates/
│   └── index.html         # 前端介面
├── database/              # 資料庫相關檔案
│   ├── sales_data.db      # SQLite 資料庫
│   └── *.csv              # CSV 資料檔案
├── pretrain/              # 預訓練資料
│   ├── business_terms.md  # 業務術語
│   └── example_queries.sql # 範例查詢
├── .env                   # 環境變數
├── .gitignore            # Git 忽略檔案
└── requirements.txt       # 相依套件
```

## 安裝步驟

1. 複製專案
```bash
git clone https://github.com/yourusername/square_sql.git
cd square_sql
```

2. 建立虛擬環境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

3. 安裝相依套件
```bash
pip install -r requirements.txt
```

4. 設定環境變數
```bash
cp .env.example .env
# 編輯 .env 檔案，填入必要的設定值：
# OPENAI_API_KEY=your_api_key
```

## 使用說明

1. 啟動應用程式
```bash
python app.py
```

2. 開啟瀏覽器訪問
```
http://localhost:5000
```

## API 端點

### 1. 自然語言查詢
- 端點：`/api/nl-query`
- 方法：`POST`
- 請求格式：
```json
{
    "question": "上個月的總銷售額是多少？"
}
```

### 2. 直接 SQL 查詢
- 端點：`/api/raw-sql`
- 方法：`POST`
- 請求格式：
```json
{
    "sql": "SELECT SUM(amount) FROM sales WHERE date >= date('now', '-1 month')"
}
```

## 開發說明

- 使用 Flask 作為後端框架
- 使用 SQLite 作為資料庫
- 整合 OpenAI GPT-4 進行自然語言處理
- 支援自定義業務術語訓練
- 完整的錯誤處理和日誌記錄

## 注意事項

- 請確保 `.env` 檔案中包含有效的 OpenAI API 金鑰
- 資料庫檔案 `sales_data.db` 需要預先建立並包含正確的資料表結構
- 建議在正式環境中使用 HTTPS 以確保資料傳輸安全

## License

This project is licensed under the MIT License - see the LICENSE file for details
