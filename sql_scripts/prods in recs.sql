select "total_prod", count(*) as sum_p
from wp_wc_product_meta_lookup
where stock_status = 'instock'

union

select "prod in ord", count(distinct product_id) as sum_p 
from wp_wc_order_product_lookup

union 

select "prod in rec", count(distinct item_id) as sum_p
from recommendations
where item_id != -1