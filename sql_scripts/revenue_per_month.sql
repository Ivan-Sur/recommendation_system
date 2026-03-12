SELECT
  DATE_FORMAT(p.post_date, '%Y-%m-01') AS month_local,
  SUM(CAST(pm.meta_value AS DECIMAL(26,8))) AS revenue
FROM wp_posts p
JOIN wp_postmeta pm
  ON pm.post_id = p.ID AND pm.meta_key = '_order_total'
WHERE p.post_type = 'shop_order'
  AND p.post_status IN ('wc-processing','wc-completed')
GROUP BY DATE_FORMAT(p.post_date, '%Y-%m-01')
ORDER BY month_local;
