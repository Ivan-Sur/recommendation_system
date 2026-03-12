SELECT
  DATE_FORMAT(post_date, '%Y-%m-01') AS month_local,
  COUNT(*) AS orders_cnt
FROM wp_posts
WHERE post_type = 'shop_order'
  AND post_status IN ('wc-processing','wc-completed')
GROUP BY DATE_FORMAT(post_date, '%Y-%m-01')
ORDER BY month_local;
