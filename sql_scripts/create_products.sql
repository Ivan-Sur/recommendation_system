-- Создание таблицы товаров
DROP TABLE IF EXISTS products;
CREATE TABLE products (
  product_id BIGINT UNSIGNED PRIMARY KEY,
  max_price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  total_sales INT UNSIGNED NOT NULL DEFAULT 0,
  KEY idx_price (max_price),
  KEY idx_sales (total_sales)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Заполнение таблицы товаров из wp_wc_product_meta_lookup и wp_wc_order_product_lookup
INSERT INTO products (product_id, max_price, total_sales)
SELECT 
  pml.product_id,
  pml.max_price AS max_price,
  pml.total_sales AS total_sales
FROM wp_wc_product_meta_lookup pml
where stock_status = 'instock';

select * from products
