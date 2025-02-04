from square.client import Client
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 載入環境變數
load_dotenv()

# 初始化 Square client
client = Client(
    access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
    environment='production'
)

def get_sales_data():
    # 設定時區為台北時間
    tz = pytz.timezone('Asia/Taipei')
    
    # 計算時間範圍（一週）
    end_time = datetime.now(tz)
    start_time = end_time - timedelta(days=7)
    
    # 商店位置 ID
    location_ids = ["LMDN6Z5DKNJ2P"]  # 只查詢 Taiwanway
    
    try:
        all_sales_data = []
        
        for location_id in location_ids:
            print(f"\n查詢位置 ID: {location_id} 的交易...")
            
            cursor = None
            total_payments = 0
            
            while True:
                # 使用 Payments API 獲取交易資訊
                result = client.payments.list_payments(
                    begin_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    location_id=location_id,
                    cursor=cursor,
                    limit=200
                )

                if result.is_success():
                    payments = result.body.get("payments", [])
                    total_payments += len(payments)
                    print(f"已獲取 {total_payments} 筆交易")
                    
                    # 準備資料列表
                    for payment in payments:
                        payment_time = datetime.fromisoformat(payment["created_at"].replace('Z', '+00:00')).astimezone(tz)
                        payment_date = payment_time.date()
                        
                        # 獲取訂單資訊
                        order_id = payment.get("order_id")
                        items = []
                        if order_id:
                            order_result = client.orders.retrieve_order(
                                order_id=order_id
                            )
                            if order_result.is_success():
                                order = order_result.body.get("order")
                                if order:
                                    items = order.get("line_items", [])
                        
                        # 如果有訂單資訊，則記錄每個商品
                        if items:
                            for item in items:
                                quantity = float(item.get("quantity", 0))
                                base_price = float(item.get("base_price_money", {}).get("amount", 0)) / 100.0
                                total_money = float(item.get("total_money", {}).get("amount", 0)) / 100.0
                                
                                all_sales_data.append({
                                    "商店位置": location_id,
                                    "日期": payment_date,
                                    "時間": payment_time.strftime("%H:%M:%S"),
                                    "交易 ID": payment["id"],
                                    "商品名稱": item.get("name", "未知商品"),
                                    "數量": quantity,
                                    "單價": base_price,
                                    "總金額": total_money
                                })
                        else:
                            # 如果沒有訂單資訊，只記錄交易金額
                            total_money = float(payment.get("total_money", {}).get("amount", 0)) / 100.0
                            all_sales_data.append({
                                "商店位置": location_id,
                                "日期": payment_date,
                                "時間": payment_time.strftime("%H:%M:%S"),
                                "交易 ID": payment["id"],
                                "商品名稱": "未知商品",
                                "數量": 1,
                                "單價": total_money,
                                "總金額": total_money
                            })
                    
                    # 檢查是否有更多資料
                    cursor = result.body.get("cursor")
                    if not cursor:
                        break
                else:
                    print(f"查詢位置 {location_id} 時發生錯誤:", result.errors)
                    break
        
        # 轉換成 DataFrame
        df = pd.DataFrame(all_sales_data)
        
        if not df.empty:
            # 顯示每個商店每天的銷售總額
            print("\n每日銷售總額：")
            print("-" * 50)
            daily_total = df.groupby(["商店位置", "日期"])["總金額"].sum()
            for (location, date), total in daily_total.items():
                print(f"商店 {location} - {date}: ${total:.2f} USD")
            
            # 顯示商品銷售明細
            print("\n商品銷售明細：")
            print("-" * 50)
            product_summary = df.groupby(["商店位置", "商品名稱"]).agg({
                "數量": "sum",
                "總金額": "sum"
            }).sort_values("總金額", ascending=False)
            
            print(product_summary)
            
            # 顯示交易統計
            print("\n交易統計：")
            print("-" * 50)
            for location_id in location_ids:
                location_df = df[df["商店位置"] == location_id]
                if not location_df.empty:
                    print(f"\n商店 {location_id}:")
                    print(f"總交易筆數：{len(location_df['交易 ID'].unique())}")
                    print(f"平均交易金額：${location_df.groupby('交易 ID')['總金額'].sum().mean():.2f} USD")
                    print(f"最大交易金額：${location_df.groupby('交易 ID')['總金額'].sum().max():.2f} USD")
                    print(f"最小交易金額：${location_df.groupby('交易 ID')['總金額'].sum().min():.2f} USD")
            
            return df
        else:
            print("這段期間沒有任何銷售記錄")
            return None
    
    except Exception as e:
        print("發生錯誤:", str(e))
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    df = get_sales_data() 