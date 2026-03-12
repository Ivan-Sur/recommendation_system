CREATE TABLE IF NOT EXISTS ml_interactions_guest (
  order_id BIGINT UNSIGNED NOT NULL,
  user_key CHAR(64) NOT NULL,          -- SHA-256 hex
  email_norm VARCHAR(320) NULL,        -- можно потом удалить
  product_id BIGINT UNSIGNED NOT NULL,
  dt DATETIME NOT NULL,
  qty DOUBLE NOT NULL,
  net_revenue DOUBLE NOT NULL,
  PRIMARY KEY (order_id, product_id),
  KEY idx_user_dt (user_key, dt),
  KEY idx_product_dt (product_id, dt)
);
REPLACE INTO ml_interactions_guest (order_id, user_key, email_norm, product_id, dt, qty, net_revenue)
SELECT
  opl.order_id,
  SHA2(LOWER(TRIM(bill.meta_value)), 256) AS user_key,
  LOWER(TRIM(bill.meta_value)) AS email_norm,
  opl.product_id,
  opl.date_created,
  opl.product_qty,
  opl.product_net_revenue
FROM wp_wc_order_product_lookup opl
JOIN wp_postmeta bill
  ON bill.post_id = opl.order_id AND bill.meta_key = '_billing_email'
WHERE bill.meta_value IS NOT NULL
  AND bill.meta_value <> '';

