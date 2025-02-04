from square.client import Client
import sqlite3
import os
from dotenv import load_dotenv
import pytz
from datetime import datetime, timedelta

def download_transactions(begin_time, end_time, client, location_id):
    """
    使用 Square SDK 的 ListPayments 取得指定期間內的交易資料
    """
    try:
        all_payments = []
        cursor = None
        
        while True:
            result = client.payments.list_payments(
                begin_time=begin_time,
                end_time=end_time,
                location_id=location_id,
                cursor=cursor,
                limit=200
            )
            
            if result.is_success():
                payments = result.body.get("payments", [])
                all_payments.extend(payments)
                
                cursor = result.body.get("cursor")
                if not cursor:
                    break
            else:
                print("發生錯誤:", result.errors)
                break
                
        return all_payments
    except Exception as e:
        print("下載交易資料時發生錯誤:", str(e))
        return []

def create_db(db_path):
    """
    建立 SQLite 資料庫，建立 transactions 與 sales 資料表（若不存在的話）
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            amount INTEGER,
            currency TEXT,
            created_at TEXT,
            status TEXT,
            order_id TEXT,
            receipt_number TEXT,
            source_type TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            store_id TEXT,
            date TEXT,
            time TEXT,
            product_name TEXT,
            product_category TEXT,
            quantity REAL,
            unit_price REAL,
            total_amount REAL
        )
    ''')
    conn.commit()
    return conn

def insert_transactions(conn, transactions):
    """
    將取得的交易資料插入到 SQLite 資料庫中的 transactions 資料表
    """
    c = conn.cursor()
    for txn in transactions:
        txn_id = txn.get("id")
        amount_money = txn.get("amount_money", {})
        amount = amount_money.get("amount")
        currency = amount_money.get("currency")
        created_at = txn.get("created_at")
        status = txn.get("status")
        order_id = txn.get("order_id")
        receipt_number = txn.get("receipt_number")
        source_type = txn.get("source_type")
        
        c.execute(
            """
            INSERT OR REPLACE INTO transactions 
            (id, amount, currency, created_at, status, order_id, receipt_number, source_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (txn_id, amount, currency, created_at, status, order_id, receipt_number, source_type)
        )
    conn.commit()

def insert_sales_data(conn, sales_data):
    """
    將取得的商品銷售資料插入到 SQLite 資料庫中的 sales 資料表
    """
    c = conn.cursor()
    for record in sales_data:
        c.execute(
            """
            INSERT INTO sales (transaction_id, store_id, date, time, product_name, product_category, quantity, unit_price, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["transaction_id"],
                record["store_id"],
                record["date"],
                record["time"],
                record["product_name"],
                record["product_category"],
                record["quantity"],
                record["unit_price"],
                record["total_amount"]
            )
        )
    conn.commit()

def get_product_category(product_name):
    """
    根據商品名稱分類
    """
    product_name = product_name.lower()
    if "noodle" in product_name or "麵" in product_name:
        return "主食"
    elif "rice" in product_name or "飯" in product_name:
        return "主食"
    elif "tea" in product_name or "茶" in product_name:
        return "飲品"
    elif "coffee" in product_name or "咖啡" in product_name:
        return "飲品"
    elif "cake" in product_name or "蛋糕" in product_name:
        return "甜點"
    elif "cookie" in product_name or "餅乾" in product_name:
        return "零食"
    elif "mug" in product_name or "杯" in product_name:
        return "商品"
    else:
        return "其他"

def main():
    # 載入環境變數
    load_dotenv()
    
    # 初始化 Square client
    client = Client(
        access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
        environment='production'
    )
    
    # 設定時區為台北時間
    tz = pytz.timezone('Asia/Taipei')
    
    # 使用 Taiwanway 的 location ID
    location_id = "LMDN6Z5DKNJ2P"  # 固定 ID
    
    # 資料庫路徑
    db_path = "transactions.db"
    
    # 詢問使用者選擇下載模式
    print("請選擇下載模式：")
    print("1. 從頭下載（從 2024-04-01 到今天）")
    print("2. 接續下載（從資料庫中最新交易時間到今天）")
    mode = input("請輸入 1 或 2：").strip()
    
    if mode == "1":
        print("執行從頭下載模式...")
        begin_time_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=tz)
        end_time_dt = datetime.now(tz)
    elif mode == "2":
        print("執行接續下載模式...")
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT MAX(created_at) FROM transactions")
                row = c.fetchone()
                conn.close()
                if row is None or row[0] is None:
                    print("資料庫中無交易資料，將從頭下載")
                    begin_time_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=tz)
                else:
                    begin_time_dt = datetime.fromisoformat(row[0].replace("Z", "+00:00")).astimezone(tz)
                    # 為避免重複，將起始時間加 1 秒
                    begin_time_dt += timedelta(seconds=1)
            except Exception as e:
                print("讀取資料庫失敗，將從頭下載，錯誤：", str(e))
                begin_time_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=tz)
        else:
            print("資料庫不存在，將從頭下載")
            begin_time_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=tz)
        end_time_dt = datetime.now(tz)
    else:
        print("未輸入正確模式，預設從頭下載")
        begin_time_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=tz)
        end_time_dt = datetime.now(tz)
    
    # 轉換為 ISO 格式
    begin_time_str = begin_time_dt.isoformat()
    end_time_str = end_time_dt.isoformat()
    
    print(f"下載時間範圍：{begin_time_str} 到 {end_time_str}")
    transactions = download_transactions(begin_time_str, end_time_str, client, location_id)
    print(f"下載完成，共 {len(transactions)} 筆交易資料")
    
    if len(transactions) > 0:
        print("建立或更新 SQLite 資料庫並儲存資料...")
        conn = create_db(db_path)
        insert_transactions(conn, transactions)
        
        # 根據每筆交易查詢訂單中的商品明細
        sales_records = []
        for txn in transactions:
            created_at = txn.get("created_at")
            try:
                payment_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).astimezone(tz)
            except Exception as e:
                print(f"解析時間錯誤: {created_at}, 錯誤: {e}")
                continue
            date_str = payment_time.strftime("%Y-%m-%d")
            time_str = payment_time.strftime("%H:%M:%S")
            trans_id = txn.get("id")
            order_id = txn.get("order_id")
            
            if order_id:
                order_result = client.orders.retrieve_order(order_id=order_id)
                if order_result.is_success():
                    order = order_result.body.get("order", {})
                    items = order.get("line_items", [])
                    if items:
                        for item in items:
                            quantity = float(item.get("quantity", 0))
                            unit_price = float(item.get("base_price_money", {}).get("amount", 0)) / 100.0
                            total_amount = float(item.get("total_money", {}).get("amount", 0)) / 100.0
                            product_name = item.get("name", "未知商品")
                            product_category = get_product_category(product_name)
                            sales_records.append({
                                "transaction_id": trans_id,
                                "store_id": location_id,
                                "date": date_str,
                                "time": time_str,
                                "product_name": product_name,
                                "product_category": product_category,
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "total_amount": total_amount
                            })
                    else:
                        total_payment = float(txn.get("amount_money", {}).get("amount", 0)) / 100.0
                        sales_records.append({
                            "transaction_id": trans_id,
                            "store_id": location_id,
                            "date": date_str,
                            "time": time_str,
                            "product_name": "未知商品",
                            "product_category": "其他",
                            "quantity": 1,
                            "unit_price": total_payment,
                            "total_amount": total_payment
                        })
                else:
                    total_payment = float(txn.get("amount_money", {}).get("amount", 0)) / 100.0
                    sales_records.append({
                        "transaction_id": trans_id,
                        "store_id": location_id,
                        "date": date_str,
                        "time": time_str,
                        "product_name": "未知商品",
                        "product_category": "其他",
                        "quantity": 1,
                        "unit_price": total_payment,
                        "total_amount": total_payment
                    })
            else:
                total_payment = float(txn.get("amount_money", {}).get("amount", 0)) / 100.0
                sales_records.append({
                    "transaction_id": trans_id,
                    "store_id": location_id,
                    "date": date_str,
                    "time": time_str,
                    "product_name": "未知商品",
                    "product_category": "其他",
                    "quantity": 1,
                    "unit_price": total_payment,
                    "total_amount": total_payment
                })
        
        if sales_records:
            insert_sales_data(conn, sales_records)
            print(f"已儲存 {len(sales_records)} 筆商品銷售資料到 sales 資料表。")
        else:
            print("沒有找到任何商品銷售明細。")
        
        conn.close()
        print("資料已成功存入 SQLite 資料庫。")
    else:
        print("警告：沒有找到任何交易資料，請確認：")
        print("1. Access Token 是否正確")
        print("2. 時間範圍是否正確")
        print("3. 該時間範圍內是否有交易紀錄")

if __name__ == "__main__":
    main() 