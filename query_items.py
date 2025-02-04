import sqlite3

def query_items(db_path, output_md):
    # 連線到 SQLite 資料庫
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查詢 sales 資料表的總筆數（所有記錄數）
    cursor.execute("SELECT COUNT(*) FROM sales")
    total_items = cursor.fetchone()[0]
    print(f"DEBUG: Total records in sales table: {total_items}")

    # 查詢 sales 資料表中不重複的產品名稱筆數（假設 Item 欄位儲存產品名稱）
    cursor.execute("SELECT COUNT(DISTINCT Item) FROM sales")
    distinct_items = cursor.fetchone()[0]
    print(f"DEBUG: Distinct items in 'Item' column: {distinct_items}")

    # 新增品項列表查詢
    cursor.execute("""
        SELECT DISTINCT Item 
        FROM sales 
        ORDER BY Item
    """)
    items = [row[0] for row in cursor.fetchall()]
    print(f"DEBUG: Retrieved {len(items)} distinct items")  # 保留debug資訊

    conn.close()

    # 將查詢結果寫入 Markdown 格式文件 items.md
    with open(output_md, "w", encoding="utf-8") as f:
        # 保留既有統計資料
        f.write("# 銷售品項報告\n\n")
        f.write(f"## 統計摘要\n- 總銷售記錄數: {total_items}\n")
        f.write(f"- 獨特品項數量: {distinct_items}\n\n")
        
        # 新增品項清單表格
        f.write("## 完整品項清單\n| 品項名稱 |\n|----------|\n")
        for item in items:
            f.write(f"| {item} |\n")

if __name__ == "__main__":
    db_path = "sales_data.db"  # 資料庫儲存位置，請確認此路徑正確
    output_md = "items.md"     # 輸出的 Markdown 檔案
    query_items(db_path, output_md)
    print(f"查詢結果已寫入 {output_md}") 