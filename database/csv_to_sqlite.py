import sqlite3
import pandas as pd
import os
from pathlib import Path
from tabulate import tabulate

def clean_currency(value):
    """
    處理美金 (USD) 貨幣字串轉換為浮點數：
    目前僅針對包含 '$' 與逗號格式的美金欄位進行轉換，
    如遇其他幣別則需要額外處理。
    """
    if isinstance(value, str):
        try:
            # 移除美金符號及逗號，例如 "$1,234.56" 轉換為 1234.56
            return float(value.replace('$', '').replace(',', ''))
        except ValueError:
            return 0.0
    return value

def clean_date(value):
    """加強日期處理：處理各種空值格式和時區"""
    if pd.isnull(value) or str(value).lower() in ['', 'nan', 'nat', 'none', 'null']:
        return None
    try:
        # 先嘗試直接轉換日期格式
        return pd.to_datetime(value).strftime('%Y-%m-%d')
    except Exception as e:
        print(f"日期解析錯誤: {value} ({str(e)})")
        return None

def import_csv_to_db(csv_folder, db_path):
    # Debug: 印出 CSV 資料夾中的所有檔案
    print("Debug: CSV folder 路徑內容:", os.listdir(csv_folder))
    
    # 建立資料庫連線
    conn = sqlite3.connect(db_path)
    
    # 動態建立資料表結構 (新增部分)
    sample_csv = next(Path(csv_folder).glob("*.csv"), None)
    if not sample_csv:
        print("錯誤: 找不到CSV檔案")
        return
    
    # 自動偵測CSV結構
    df_sample = pd.read_csv(sample_csv, sep=None, engine='python', encoding='utf-8', nrows=1)
    
    # 自動生成CREATE TABLE語句
    columns = []
    for col in df_sample.columns:
        # 判斷資料類型 (簡化版)
        dtype = 'TEXT'
        if any(kw in col.lower() for kw in ['price', 'sales', 'tax', 'amount', 'qty']):
            dtype = 'REAL'
        elif 'date' in col.lower():
            dtype = 'TEXT'  # SQLite沒有DATE類型
        columns.append(f'[{col}] {dtype}')
    
    create_table_sql = f'''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {', '.join(columns)}
    )
    '''
    conn.execute(create_table_sql)
    conn.commit()

    # 修正CSV檔案篩選邏輯
    csv_files = [f for f in Path(csv_folder).glob("*.csv") if f.is_file() and f.suffix.lower() == '.csv']
    print(f"Debug: 找到有效 CSV 檔案數量: {len(csv_files)}")
    
    for csv_file in csv_files:
        print(f"處理檔案: {csv_file}")
        try:
            df = pd.read_csv(csv_file, sep=None, engine='python', encoding='utf-8')
            # 新增資料清洗步驟
            df = df.drop_duplicates().reset_index(drop=True)  # 移除重複資料
            print(f"Debug: {csv_file} 讀取結果, shape: {df.shape}")
            
            # 日期欄位處理
            if 'Date' in df.columns:
                df['Date'] = df['Date'].apply(clean_date)
            
            # 貨幣欄位處理
            currency_columns = ['Gross Sales', 'Net Sales', 'Tax', 'Discounts']
            for col in currency_columns:
                if col in df.columns:
                    df[col] = df[col].apply(clean_currency)
            
            # 移除欄位過濾，保留所有欄位
            df.to_sql('sales', conn, if_exists='append', index=False)
            print(f"成功匯入 {csv_file}")
        except Exception as e:
            print(f"寫入 {csv_file} 時發生錯誤: {e}")
            print("詳細錯誤資訊:", str(e))
            continue
    
    conn.close()
    print(f"成功處理 {len(csv_files)} 個 CSV 檔案")

def visualize_schema(db_path):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # 取得schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        schema = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                schema.append({
                    'Table': table_name,
                    'Column': col[1],
                    'Type': col[2],
                    'Nullable': 'NO' if col[3] else 'YES',
                    'Primary Key': 'YES' if col[5] else 'NO'
                })
        
        print("資料庫結構:\n")
        print(tabulate(schema, headers="keys", tablefmt="psql"))

        # 修正統計部分
        print("\n=== 資料統計 ===")
        cursor.execute("SELECT COUNT(*) FROM sales")
        total = cursor.fetchone()[0]
        print(f"總記錄數: {total:,}")

        cursor.execute("SELECT MIN(Date), MAX(Date) FROM sales")
        min_date, max_date = cursor.fetchone()
        print(f"日期範圍: {min_date} 至 {max_date}")

        # 修正貨幣欄位統計
        currency_cols = ['[Gross Sales]', '[Net Sales]', '[Tax]']
        for col in currency_cols:
            cursor.execute(f"SELECT SUM({col}) FROM sales")
            total = cursor.fetchone()[0] or 0
            print(f"{col.replace('[', '').replace(']', '')} 總和: ${total:,.2f}")
    finally:
        conn.close()

def print_items(db_path):
    """
    印出 sales 表中的總筆數與 distinct items
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM sales")
        total_rows = cursor.fetchone()[0]
        print(f"總記錄數: {total_rows}")

        cursor.execute("SELECT DISTINCT Item FROM sales")
        items = cursor.fetchall()
        items = [item[0] for item in items]
        print(f"Distinct 'Item' 數量: {len(items)}")
        print("Items:")
        for item in items:
            print(item)
    except Exception as e:
        print(f"查詢 items 時發生錯誤: {e}")
    finally:
        conn.close()

def show_top_10_records(db_path):
    """顯示資料庫中前10筆記錄"""
    conn = sqlite3.connect(db_path)
    try:
        query = """
        SELECT Date, Time, Category, Item, Qty, [Gross Sales], [Net Sales], Tax
        FROM sales
        LIMIT 10
        """
        df = pd.read_sql_query(query, conn)
        print("\n=== 前10筆記錄 ===")
        print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))
    except Exception as e:
        print(f"查詢前10筆記錄時發生錯誤: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "sales_data.db"  # 資料庫儲存位置
    csv_folder = "./"          # CSV 檔案所在的資料夾，可依需求調整
    
    import_csv_to_db(csv_folder, db_path)
    visualize_schema(db_path)
    show_top_10_records(db_path)
    print_items(db_path) 