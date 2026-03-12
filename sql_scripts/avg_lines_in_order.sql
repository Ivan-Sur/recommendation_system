SELECT
  AVG(x.lines_cnt) AS avg_lines_per_order,
  MIN(x.lines_cnt) AS min_lines_per_order,
  MAX(x.lines_cnt) AS max_lines_per_order
FROM (
  SELECT oi.order_id, COUNT(*) AS lines_cnt
  FROM wp_woocommerce_order_items oi
  JOIN wp_posts p ON p.ID = oi.order_id
  WHERE p.post_type = 'shop_order'
    AND p.post_status IN ('wc-processing','wc-completed')
    AND oi.order_item_type = 'line_item'
  GROUP BY oi.order_id
) x;
