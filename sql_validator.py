import sqlparse
import re
from typing import Tuple, List

ALLOWED_TABLES = {'sales'}
ALLOWED_COLUMNS = {
    'id', 'Date', 'Time', 'Time Zone', 'Category', 'Item', 'Qty',
    'Price Point Name', 'SKU', 'Modifiers Applied', 'Gross Sales',
    'Discounts', 'Net Sales', 'Tax', 'Transaction ID', 'Payment ID',
    'Device Name', 'Notes', 'Details', 'Event Type', 'Location',
    'Dining Option', 'Customer ID', 'Customer Name', 'Customer Reference ID',
    'Unit', 'Count', 'GTIN', 'Itemization Type', 'Fulfillment Note',
    'Channel', 'Token'
}

def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    驗證 SQL 查詢是否安全
    
    Args:
        sql: SQL 查詢字串
    
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    try:
        # 解析 SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "無效的 SQL 查詢"
        
        stmt = parsed[0]
        
        # 檢查是否為 SELECT 語句
        if stmt.get_type().upper() != 'SELECT':
            return False, "只允許 SELECT 查詢"
        
        # 檢查是否包含危險關鍵字
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE']
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if f" {keyword} " in f" {sql_upper} ":
                return False, f"不允許使用 {keyword} 關鍵字"
        
        # 檢查表格名稱
        tables = extract_tables(sql)
        if not tables:
            return False, "無法識別查詢的表格"
            
        for table in tables:
            if table.lower() not in ALLOWED_TABLES:
                return False, f"不允許查詢表格: {table}"
        
        # 不再檢查欄位名稱，允許使用別名和計算欄位
        return True, "SQL 查詢有效"
    
    except Exception as e:
        return False, f"SQL 驗證錯誤: {str(e)}"

def extract_tables(sql: str) -> List[str]:
    """
    從 SQL 查詢中提取表格名稱
    """
    tables = []
    parsed = sqlparse.parse(sql)[0]
    
    def extract_from_token(token):
        if isinstance(token, sqlparse.sql.Identifier):
            tables.append(token.get_name())
        elif isinstance(token, sqlparse.sql.TokenList):
            for sub_token in token.tokens:
                extract_from_token(sub_token)
    
    # 尋找 FROM 子句
    from_seen = False
    for token in parsed.tokens:
        if token.is_keyword and token.normalized == 'FROM':
            from_seen = True
            continue
        if from_seen:
            if token.is_whitespace:
                continue
            if isinstance(token, (sqlparse.sql.Identifier, sqlparse.sql.TokenList)):
                extract_from_token(token)
            break
            
    return tables

def extract_columns(sql: str) -> List[str]:
    """
    從 SQL 查詢中提取欄位名稱
    """
    columns = []
    parsed = sqlparse.parse(sql)[0]
    
    def extract_from_token(token):
        if isinstance(token, sqlparse.sql.Identifier):
            # 處理 COUNT(*) 等函數
            if token.has_alias():
                columns.append(token.get_alias())
            else:
                columns.append(token.get_name())
        elif isinstance(token, sqlparse.sql.Function):
            # 處理函數名稱
            pass
        elif isinstance(token, sqlparse.sql.TokenList):
            for sub_token in token.tokens:
                extract_from_token(sub_token)
    
    # 尋找 SELECT 子句
    select_seen = False
    for token in parsed.tokens:
        if token.is_keyword and token.normalized == 'SELECT':
            select_seen = True
            continue
        if select_seen:
            if token.is_whitespace:
                continue
            if token.is_keyword and token.normalized in ('FROM', 'WHERE', 'GROUP', 'ORDER'):
                break
            extract_from_token(token)
            
    return columns 