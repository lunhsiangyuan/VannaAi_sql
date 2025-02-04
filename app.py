from flask import Flask, request, render_template_string
import sqlite3
import os
from dotenv import load_dotenv
import pandas as pd
from openai import OpenAI

# 載入環境變數
load_dotenv()

# 檢查 OPENAI_API_KEY 是否存在
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise Exception("請在 .env 檔案中設定有效的 OPENAI_API_KEY。")

app = Flask(__name__)

# 初始化 OpenAI client
client = OpenAI(api_key=openai_key)

def get_db_connection():
    """建立資料庫連接並返回連接物件"""
    try:
        conn = sqlite3.connect('transactions.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {str(e)}")
        return None

def get_schema_info():
    """改進版 schema 獲取函式，包含完整 DDL 與業務註釋"""
    try:
        conn = get_db_connection()
        if conn is None:
            raise Exception("無法連接到資料庫")
        
        cursor = conn.cursor()
        
        # 獲取完整 DDL 定義
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
        ddls = [f"-- {row[0]} 的完整結構\n{row[1]};" for row in cursor.fetchall()]
        
        # 獲取外鍵約束資訊
        cursor.execute("PRAGMA foreign_key_list(sales)")
        fks = ["-- 外鍵約束\nFOREIGN KEY({}) REFERENCES {}({})".format(
            fk[3], fk[2], fk[4]
        ) for fk in cursor.fetchall()]
        
        # 業務相關註釋
        business_notes = [
            "-- 重要業務規則",
            "-- 1. total_amount 單位為美元",
            "-- 2. date 格式為 ISO 8601 (YYYY-MM-DD)",
            "-- 3. status 可能值: COMPLETED, CANCELED"
        ]
        
        conn.close()
        return "\n\n".join(ddls + fks + business_notes)
    except Exception as e:
        print(f"獲取資料庫結構時發生錯誤: {str(e)}")
        return None

def sanitize_sql(sql):
    # 檢查是否以三個反引號開始
    if sql.startswith("```"):
        # 分割成多行
        lines = sql.splitlines()
        # 如果第一行是 ```sql，則移除該行
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # 如果最後一行是 ```，也移除
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return sql.strip()

def generate_sql(question):
    """使用改進版 prompt 生成 SQL"""
    try:
        schema = get_schema_info()
        if not schema:
            return None
        
        prompt = f"""嚴格按照以下規則生成 SQL：
1. 只使用 sales 和 transactions 表
2. 日期過濾使用 date() 函數
3. 排除 status != 'COMPLETED' 的記錄
4. 金額單位為美元
5. 不要包含 Markdown 格式

資料庫結構：
{schema}

問題：{question}

SQL 查詢："""
        
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "你是精通 SQL 的資料工程師，熟悉餐飲業銷售分析"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        sql = sanitize_sql(response.choices[0].message.content)
        print(f"生成的 SQL 查詢: {sql}")
        return sql
    except Exception as e:
        print(f"生成 SQL 查詢時發生錯誤: {str(e)}")
        return None

@app.route("/", methods=["GET"])
def home():
    return render_template_string(html_template)

@app.route("/query", methods=["POST"])
def query():
    question = request.form.get("question")
    try:
        sql_query = generate_sql(question)
        print("DEBUG: 使用者輸入問題:", question)
        print("DEBUG: 生成的 SQL 查詢:", sql_query)

        if not sql_query or not isinstance(sql_query, str):
            error_message = "無法生成有效的 SQL 查詢，請檢查問題描述。"
            print("DEBUG ERROR:", error_message)
            return render_template_string(html_template, sql_query="", error=error_message)
        
        conn = get_db_connection()
        if conn is None:
            error_message = "無法連接到資料庫"
            print("DEBUG ERROR:", error_message)
            return render_template_string(html_template, sql_query=sql_query, error=error_message)
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [description[0] for description in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            conn.close()
            return render_template_string(html_template, sql_query=sql_query, results=results, columns=columns)
        except Exception as e:
            error_message = f"執行 SQL 查詢發生錯誤: {str(e)}"
            print("DEBUG ERROR:", error_message)
            if conn:
                conn.close()
            return render_template_string(html_template, sql_query=sql_query, error=error_message)
    except Exception as e:
        error_message = f"生成 SQL 查詢時發生錯誤: {str(e)}"
        print("DEBUG ERROR:", error_message)
        return render_template_string(html_template, error=error_message)

# HTML 範本
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>自然語言查詢 SQL DB</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .form-group { margin: 20px 0; }
        input[type="text"] { width: 80%; padding: 8px; }
        button { padding: 8px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background: #45a049; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 8px; text-align: left; border: 1px solid #ddd; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h1>自然語言查詢 SQL DB</h1>
        <div class="form-group">
            <form method="post" action="/query">
                <label for="question">請輸入查詢問題：</label><br>
                <input type="text" id="question" name="question" placeholder="例如：最近一週的銷售總額是多少？" required>
                <button type="submit">查詢</button>
            </form>
        </div>
        {% if sql_query %}
            <h2>生成的 SQL 查詢：</h2>
            <pre>{{ sql_query }}</pre>
        {% endif %}
        {% if results %}
            <h2>查詢結果：</h2>
            <div style="overflow-x: auto;">
                <table>
                    <tr>
                        {% for col in columns %}
                        <th>{{ col }}</th>
                        {% endfor %}
                    </tr>
                    {% for row in results %}
                    <tr>
                        {% for col in row %}
                        <td>{{ col }}</td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </table>
            </div>
        {% endif %}
        {% if error %}
            <h2 class="error">錯誤：</h2>
            <pre class="error">{{ error }}</pre>
        {% endif %}
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    print("正在啟動應用程式...")
    print("請在瀏覽器中訪問 http://localhost:5000")
    app.run(debug=True)

# 在初始化 Vanna 後加入訓練資料
vn = MyVanna(config={
    "api_key": openai_key,
    "model": "gpt-4-turbo-preview",
    "temperature": 0,
    "max_tokens": 1000
})

# 加入 DDL 訓練
vn.train(ddl="""
CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    date TEXT NOT NULL,
    product_name TEXT NOT NULL,
    product_category TEXT,
    quantity INTEGER,
    unit_price REAL,
    total_amount REAL,
    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
);

CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('COMPLETED', 'CANCELED'))
);
""")

# 加入業務規則訓練
vn.train(documentation="""
重要業務定義：
1. 「最近一週」指從查詢當天往前推 7 天
2. 有效交易需滿足 status = 'COMPLETED'
3. 熱門商品定義：當週銷售量前 10 名
""")

# 加入範例 SQL 查詢
vn.train(sql="""
-- 範例查詢 1：牛肉麵最近一週銷售
SELECT 
    date,
    SUM(quantity) AS 總數量,
    SUM(total_amount) AS 總金額
FROM sales
WHERE 
    product_name = '牛肉麵'
    AND date >= date('now', '-7 days')
    AND date <= date('now')
GROUP BY date
ORDER BY date DESC;

-- 範例查詢 2：各時段銷售統計
SELECT 
    CASE
        WHEN time(time) BETWEEN '06:00' AND '10:59' THEN '早餐'
        WHEN time(time) BETWEEN '11:00' AND '13:59' THEN '午餐'
        WHEN time(time) BETWEEN '14:00' AND '16:59' THEN '下午茶'
        ELSE '其他'
    END AS 時段,
    SUM(total_amount) AS 總金額
FROM sales
WHERE date >= '2024-01-01'
GROUP BY 時段;
""") 