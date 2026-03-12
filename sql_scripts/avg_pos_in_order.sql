SELECT
  AVG(x.units_cnt) AS avg_units_per_order,
  MIN(x.units_cnt) AS min_units_per_order,
  MAX(x.units_cnt) AS max_units_per_order
FROM (
  SELECT
    oi.order_id,
    SUM(CAST(oim.meta_value AS DECIMAL(20,4))) AS units_cnt
  FROM wp_woocommerce_order_items oi
  JOIN wp_posts p ON p.ID = oi.order_id
  JOIN wp_woocommerce_order_itemmeta oim
    ON oim.order_item_id = oi.order_item_id
   AND oim.meta_key = '_qty'
  WHERE p.post_type = 'shop_order'
    AND p.post_status IN ('wc-processing','wc-completed')
    AND oi.order_item_type = 'line_item'
  GROUP BY oi.order_id
) x;
