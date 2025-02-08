from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import sqlite3
from sql_validator import validate_sql
import logging
from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore
import traceback
import pandas as pd

# 載入環境變數
load_dotenv()

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)

    def run_sql(self, sql):
        """重寫 run_sql 方法以使用 SQLite"""
        try:
            conn = sqlite3.connect('database/sales_data.db')
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"執行 SQL 失敗: {str(e)}")
            raise

app = Flask(__name__)

# 初始化 Vanna
vn = MyVanna(
    config={
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-4',
        'temperature': 0.1
    }
)

# 連接資料庫並訓練
def init_vanna():
    """初始化 Vanna"""
    try:
        logger.info("開始初始化 Vanna...")
        
        # 連接資料庫
        vn.connect_to_sqlite('database/sales_data.db')
        logger.info("Vanna 初始化完成")
        
        # 訓練資料
        train_data()
        
    except Exception as e:
        logger.error(f"Vanna 初始化失敗: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def train_data():
    """訓練所有必要的資料"""
    try:
        logger.info("開始訓練資料...")
        
        # 訓練 schema
        conn = sqlite3.connect('database/sales_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            if table[0]:
                logger.info(f"訓練表格 schema: {table[0]}")
                vn.train(ddl=table[0])
        
        # 訓練業務術語
        try:
            with open('pretrain/business_terms.md', 'r', encoding='utf-8') as f:
                terms = f.read()
                logger.info("訓練業務術語...")
                vn.train(documentation=terms)
        except Exception as e:
            logger.error(f"訓練業務術語失敗: {str(e)}")
        
        # 訓練範例查詢
        try:
            with open('pretrain/example_queries.sql', 'r', encoding='utf-8') as f:
                queries = f.read().split(';')
                logger.info("訓練範例查詢...")
                for query in queries:
                    if query.strip():
                        vn.train(sql=query.strip())
        except Exception as e:
            logger.error(f"訓練範例查詢失敗: {str(e)}")
            
        logger.info("資料訓練完成")
        
    except Exception as e:
        logger.error(f"訓練資料時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        conn.close()

# 全域錯誤處理
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"未捕獲的異常: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "伺服器內部錯誤",
        "details": str(e) if app.debug else None
    }), 500, {'Content-Type': 'application/json'}

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '找不到該端點'}), 404, {'Content-Type': 'application/json'}

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': '不支援的請求方法'}), 405, {'Content-Type': 'application/json'}

@app.before_request
def before_request():
    if request.path != '/' and not request.path.startswith('/static/'):
        if not request.is_json and request.method != 'GET':
            return jsonify({'error': '只接受 JSON 格式的請求'}), 400, {'Content-Type': 'application/json'}

def get_db_connection():
    """建立資料庫連線"""
    try:
        conn = sqlite3.connect('database/sales_data.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"資料庫連線失敗: {str(e)}")
        raise

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"渲染首頁失敗: {str(e)}")
        return jsonify({'error': '頁面渲染失敗'}), 500, {'Content-Type': 'application/json'}

@app.route('/api/raw-sql', methods=['POST'])
def raw_sql():
    """直接執行 SQL 查詢的端點"""
    try:
        logger.info("收到 raw-sql 請求")
        
        data = request.get_json()
        if not data or 'sql' not in data:
            return jsonify({'error': '需提供有效的 SQL 查詢字串'}), 400, {'Content-Type': 'application/json'}
            
        sql = data['sql'].strip()
        if not sql:
            return jsonify({'error': 'SQL 查詢不能為空'}), 400, {'Content-Type': 'application/json'}

        logger.info(f"準備執行 SQL 查詢: {sql}")

        # SQL 驗證
        is_valid, error_message = validate_sql(sql)
        if not is_valid:
            return jsonify({'error': f'SQL 語法錯誤: {error_message}'}), 400, {'Content-Type': 'application/json'}

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            
            if sql.strip().upper().startswith('SELECT'):
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"查詢完成，返回 {len(results)} 筆結果")
            else:
                conn.commit()
                results = {'affected_rows': cursor.rowcount}
                logger.info(f"非查詢操作完成，影響 {cursor.rowcount} 筆資料")
            
            return jsonify({
                'sql': sql,
                'results': results
            }), 200, {'Content-Type': 'application/json'}

        except sqlite3.Error as e:
            logger.error(f"資料庫錯誤: {str(e)}")
            return jsonify({'error': f'資料庫錯誤: {str(e)}'}), 400, {'Content-Type': 'application/json'}
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"處理 SQL 查詢時發生錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': '處理查詢時發生錯誤'}), 500, {'Content-Type': 'application/json'}

@app.route('/api/nl-query', methods=['POST'])
def nl_query():
    try:
        logger.info("收到自然語言查詢請求")
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': '請提供查詢問題'}), 400, {'Content-Type': 'application/json'}

        question = data['question'].strip()
        if not question:
            return jsonify({'error': '查詢問題不能為空'}), 400, {'Content-Type': 'application/json'}

        logger.info(f"處理查詢問題: {question}")
        
        try:
            sql = vn.generate_sql(question=question)
            logger.info(f"生成的 SQL: {sql}")
            
            # 驗證生成的 SQL
            is_valid, error_message = validate_sql(sql)
            if not is_valid:
                logger.error(f"生成的 SQL 無效: {error_message}")
                return jsonify({'error': f'生成的 SQL 無效: {error_message}'}), 400, {'Content-Type': 'application/json'}
            
            df = vn.run_sql(sql)
            logger.info("SQL 執行成功")
            
            return jsonify({
                'question': question,
                'sql': sql,
                'results': df.to_dict(orient='records')
            }), 200, {'Content-Type': 'application/json'}
            
        except Exception as e:
            logger.error(f"Vanna 處理失敗: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'自然語言處理失敗: {str(e)}'}), 500, {'Content-Type': 'application/json'}

    except Exception as e:
        logger.error(f"自然語言查詢錯誤: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': '處理查詢時發生錯誤'}), 500, {'Content-Type': 'application/json'}

if __name__ == '__main__':
    try:
        init_vanna()
        port = int(os.getenv('FLASK_PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"應用程式啟動失敗: {str(e)}")
        logger.error(traceback.format_exc()) 