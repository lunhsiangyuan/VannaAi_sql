from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)
DB_PATH = 'sales_data.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 讓結果以字典形式返回
    return conn

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    error = None
    query = ''
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
        except Exception as e:
            error = f"SQL 錯誤: {str(e)}"
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>SQL 查詢工具</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                textarea { width: 80%; height: 100px; padding: 8px; }
                button { padding: 8px 15px; background: #4CAF50; color: white; border: none; }
                pre { background: #f5f5f5; padding: 10px; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { padding: 8px; border: 1px solid #ddd; }
                th { background-color: #4CAF50; color: white; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Sales 資料庫查詢</h1>
                <form method="post">
                    <textarea name="query" placeholder="輸入 SQL 查詢..." required>{{ query }}</textarea><br>
                    <button type="submit">執行</button>
                </form>
                
                {% if error %}
                    <div class="error">
                        <h3>錯誤：</h3>
                        <pre>{{ error }}</pre>
                    </div>
                {% endif %}
                
                {% if results %}
                    <h3>查詢結果 ({{ results|length }} 筆)</h3>
                    <table>
                        <tr>
                            {% for col in results[0].keys() %}
                                <th>{{ col }}</th>
                            {% endfor %}
                        </tr>
                        {% for row in results %}
                            <tr>
                                {% for value in row %}
                                    <td>{{ value }}</td>
                                {% endfor %}
                            </tr>
                        {% endfor %}
                    </table>
                {% endif %}
            </div>
        </body>
        </html>
    ''', results=results, error=error, query=query)

if __name__ == '__main__':
    app.run(debug=True) 