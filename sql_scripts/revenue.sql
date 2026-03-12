SELECT
  SUM(CAST(pm.meta_value AS DECIMAL(26,8))) AS revenue_total,
  AVG(CAST(pm.meta_value AS DECIMAL(26,8))) AS aov_avg_order_value,
  MIN(CAST(pm.meta_value AS DECIMAL(26,8))) AS min_order_total,
  MAX(CAST(pm.meta_value AS DECIMAL(26,8))) AS max_order_total
FROM wp_posts p
JOIN wp_postmeta pm
  ON pm.post_id = p.ID AND pm.meta_key = '_order_total'
WHERE p.post_type = 'shop_order'
  AND p.post_status IN ('wc-processing','wc-completed');
