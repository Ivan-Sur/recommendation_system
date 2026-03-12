DROP TABLE IF EXISTS ml_split_orders;
CREATE TABLE ml_split_orders (
  order_id BIGINT UNSIGNED PRIMARY KEY,
  dt DATETIME NOT NULL,
  split ENUM('A','B') NOT NULL,
  KEY idx_split_dt (split, dt)
);

INSERT INTO ml_split_orders (order_id, dt, split)
SELECT
  t.order_id,
  t.dt,
  CASE
    WHEN t.rn <= FLOOR(0.8 * t.total_cnt) THEN 'A'
    ELSE 'B'
  END AS split
FROM (
  SELECT
    x.order_id,
    x.dt,
    ROW_NUMBER() OVER (ORDER BY x.dt, x.order_id) AS rn,
    COUNT(*) OVER () AS total_cnt
  FROM (
    SELECT order_id, MIN(dt) AS dt
    FROM ml_interactions_guest
    GROUP BY order_id
  ) x
) t;
 
 select split, count(*) from ml_split_orders group by split;