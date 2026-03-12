SELECT
  COUNT(DISTINCT CAST(oim.meta_value AS UNSIGNED)) AS unique_products_sold
FROM wp_posts p
JOIN wp_woocommerce_order_items oi
  ON oi.order_id = p.ID AND oi.order_item_type = 'line_item'
JOIN wp_woocommerce_order_itemmeta oim
  ON oim.order_item_id = oi.order_item_id
 AND oim.meta_key = '_product_id'
WHERE p.post_type = 'shop_order'
  AND p.post_status IN ('wc-processing','wc-completed');
