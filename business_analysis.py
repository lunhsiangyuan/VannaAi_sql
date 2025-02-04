from square.client import Client
import os
from dotenv import load_dotenv
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import numpy as np
from matplotlib.font_manager import FontProperties

# 設定中文字型
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

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
                    
                    for payment in payments:
                        payment_time = datetime.fromisoformat(payment["created_at"].replace('Z', '+00:00')).astimezone(tz)
                        payment_date = payment_time.date()
                        
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
                        
                        if items:
                            for item in items:
                                quantity = float(item.get("quantity", 0))
                                base_price = float(item.get("base_price_money", {}).get("amount", 0)) / 100.0
                                total_money = float(item.get("total_money", {}).get("amount", 0)) / 100.0
                                
                                all_sales_data.append({
                                    "商店位置": location_id,
                                    "日期": payment_date,
                                    "小時": payment_time.hour,
                                    "時間": payment_time.strftime("%H:%M:%S"),
                                    "交易 ID": payment["id"],
                                    "商品名稱": item.get("name", "未知商品"),
                                    "商品類別": get_product_category(item.get("name", "未知商品")),
                                    "數量": quantity,
                                    "單價": base_price,
                                    "總金額": total_money
                                })
                        else:
                            total_money = float(payment.get("total_money", {}).get("amount", 0)) / 100.0
                            all_sales_data.append({
                                "商店位置": location_id,
                                "日期": payment_date,
                                "小時": payment_time.hour,
                                "時間": payment_time.strftime("%H:%M:%S"),
                                "交易 ID": payment["id"],
                                "商品名稱": "未知商品",
                                "商品類別": "其他",
                                "數量": 1,
                                "單價": total_money,
                                "總金額": total_money
                            })
                    
                    cursor = result.body.get("cursor")
                    if not cursor:
                        break
                else:
                    print(f"查詢位置 {location_id} 時發生錯誤:", result.errors)
                    break
        
        return pd.DataFrame(all_sales_data)
    
    except Exception as e:
        print("發生錯誤:", str(e))
        import traceback
        traceback.print_exc()
        return None

def get_product_category(product_name):
    """根據商品名稱分類"""
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

def analyze_sales(df):
    if df is None or df.empty:
        print("沒有資料可分析")
        return

    # 設定圖表風格
    sns.set_style("whitegrid")
    plt.figure(figsize=(15, 10))

    # 1. 每日銷售趨勢
    plt.subplot(2, 2, 1)
    daily_sales = df.groupby("日期")["總金額"].sum()
    sns.lineplot(x=daily_sales.index, y=daily_sales.values)
    plt.title("每日銷售趨勢")
    plt.xlabel("日期")
    plt.ylabel("銷售額 (USD)")
    plt.xticks(rotation=45)

    # 2. 商品類別銷售分布
    plt.subplot(2, 2, 2)
    category_sales = df.groupby("商品類別")["總金額"].sum().sort_values(ascending=True)
    plt.barh(y=category_sales.index, width=category_sales.values)
    plt.title("商品類別銷售分布")
    plt.xlabel("銷售額 (USD)")

    # 3. 每小時客流量分析
    plt.subplot(2, 2, 3)
    hourly_traffic = df.groupby("小時")["交易 ID"].nunique()
    sns.barplot(x=hourly_traffic.index, y=hourly_traffic.values)
    plt.title("每小時客流量分布")
    plt.xlabel("小時")
    plt.ylabel("交易數")

    # 4. 熱門商品 Top 10
    plt.subplot(2, 2, 4)
    top_products = df.groupby("商品名稱")["總金額"].sum().sort_values(ascending=True).tail(10)
    plt.barh(y=top_products.index, width=top_products.values)
    plt.title("熱門商品 Top 10")
    plt.xlabel("銷售額 (USD)")

    plt.tight_layout()
    plt.show()

    # 打印銷售分析報告
    print("\n=== 銷售分析報告 ===")
    print("\n1. 整體銷售表現：")
    print(f"總銷售額: ${df['總金額'].sum():.2f}")
    print(f"總訂單數: {df['交易 ID'].nunique()}")
    print(f"平均客單價: ${df.groupby('交易 ID')['總金額'].sum().mean():.2f}")

    print("\n2. 商品類別分析：")
    category_analysis = df.groupby("商品類別").agg({
        "總金額": "sum",
        "數量": "sum",
        "交易 ID": "nunique"
    }).round(2)
    category_analysis.columns = ["銷售額", "銷售數量", "訂單數"]
    print(category_analysis)

    print("\n3. 銷售時段分析：")
    peak_hour = df.groupby("小時")["交易 ID"].nunique().idxmax()
    print(f"尖峰時段: {peak_hour}:00")
    
    # 計算每個時段的平均客單價
    hourly_avg_sales = df.groupby("小時").agg({
        "總金額": "sum",
        "交易 ID": "nunique"
    })
    hourly_avg_sales["平均客單價"] = hourly_avg_sales["總金額"] / hourly_avg_sales["交易 ID"]
    best_hour_by_avg = hourly_avg_sales["平均客單價"].idxmax()
    print(f"最高客單價時段: {best_hour_by_avg}:00 (${hourly_avg_sales['平均客單價'].max():.2f})")

if __name__ == "__main__":
    df = get_sales_data()
    if df is not None:
        analyze_sales(df) 