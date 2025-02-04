from square.client import Client
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化 Square client
client = Client(
    access_token=os.getenv('SQUARE_ACCESS_TOKEN'),
    environment='production'
)

def check_store_info():
    try:
        # 檢查商店位置
        print("檢查商店位置...")
        result = client.locations.list_locations()
        
        if result.is_success():
            locations = result.body.get("locations", [])
            if locations:
                print(f"\n找到 {len(locations)} 個商店位置：")
                print("-" * 50)
                for loc in locations:
                    print(f"位置 ID: {loc['id']}")
                    print(f"名稱: {loc['name']}")
                    print(f"地址: {loc.get('address', {}).get('address_line_1', 'N/A')}")
                    print(f"城市: {loc.get('address', {}).get('locality', 'N/A')}")
                    print(f"國家: {loc.get('address', {}).get('country', 'N/A')}")
                    print(f"狀態: {loc['status']}")
                    print(f"建立時間: {loc['created_at']}")
                    print("-" * 50)
            else:
                print("沒有找到任何商店位置")
        else:
            print("獲取商店位置時發生錯誤:", result.errors)
        
        # 檢查商家資訊
        print("\n檢查商家資訊...")
        merchant_result = client.merchants.list_merchants()
        
        if merchant_result.is_success():
            merchants = merchant_result.body.get("merchants", [])
            if merchants:
                print(f"\n找到 {len(merchants)} 個商家：")
                print("-" * 50)
                for merchant in merchants:
                    print(f"商家 ID: {merchant['id']}")
                    print(f"商家名稱: {merchant['business_name']}")
                    print(f"國家: {merchant['country']}")
                    print(f"語言: {merchant['language_code']}")
                    print(f"貨幣: {merchant['currency']}")
                    print("-" * 50)
            else:
                print("沒有找到任何商家資訊")
        else:
            print("獲取商家資訊時發生錯誤:", merchant_result.errors)
    
    except Exception as e:
        print("發生錯誤:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_store_info() 