-- Создание таблицы заказов с товарами
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  order_id BIGINT UNSIGNED NOT NULL,
  product_id BIGINT UNSIGNED NOT NULL,
  prod_qty INT UNSIGNED NOT NULL,
  customer_id VARCHAR(255),
  dt datetime not null,
  status VARCHAR(50) NOT NULL,
  PRIMARY KEY (order_id, product_id),
  KEY idx_order (order_id),
  KEY idx_product (product_id),
  KEY idx_customer_status (customer_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Заполнение таблицы заказов из wp_wc_order_product_lookup и wp_wc_order_stats
INSERT INTO orders (order_id, product_id, prod_qty, customer_id, dt, status)
SELECT DISTINCT
  opl.order_id,
  opl.product_id,
  opl.product_qty AS product_qty,
  COALESCE(os.customer_id, opl.customer_id) AS customer_id,
  opl.date_created,
  COALESCE(os.status, 'wc-pending') AS status
FROM wp_wc_order_product_lookup opl
LEFT JOIN wp_wc_order_stats os ON opl.order_id = os.order_id
WHERE opl.order_id IS NOT NULL 
  AND opl.product_id IS NOT NULL
  AND opl.product_qty > 0
  and os.status = 'wc-processing';


select * from orders