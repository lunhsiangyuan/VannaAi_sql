-- 查詢今日總銷售額
SELECT SUM("Net Sales") FROM sales WHERE DATE(Date) = DATE('now');

-- 查詢最熱銷商品前10名
SELECT Item, SUM(Qty) AS total_quantity 
FROM sales 
GROUP BY Item 
ORDER BY total_quantity DESC 
LIMIT 10;

-- 查詢各分店銷售業績
SELECT Location, SUM("Net Sales") AS total_sales 
FROM sales 
GROUP BY Location 
ORDER BY total_sales DESC; 

--我有那些牛肉麵的品項
SELECT DISTINCT Item 
FROM sales 
WHERE Item LIKE '%牛肉麵%';

-- 2025月1月的所有銷售品項
SELECT DISTINCT Item, COUNT(*) as Count
FROM sales
WHERE Date LIKE '2025-01%'
GROUP BY Item
ORDER BY Count DESC;