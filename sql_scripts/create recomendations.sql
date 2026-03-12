CREATE TABLE recommendations (
    seed_product_id INT NOT NULL,
    recommended_product_id INT NOT NULL,
    rank_item INT NOT NULL,
    score FLOAT,
    PRIMARY KEY(seed_product_id, rank_item)
);