"""
Training script for product recommendation models.
"""

import os, pickle
import pandas as pd
import numpy as np
from dotenv import load_dotenv

from db import test_connection, get_engine
from models import (
    model_cooccurrence,
    model_cosine,
    model_generalized_cosine,
    model_lift,
    model_pmi,
    model_hybrid,
    build_matrix,
    compute_cooccurrence,
)

load_dotenv()
K = int(os.getenv("K", "5"))
ALPHA = float(os.getenv("ALPHA", "0.95"))
LAM = float(os.getenv("LAM", "0.8"))
eps = 1e-9


def build_basket(orders):
    return orders.assign(v=1).pivot_table(
        index="order_id", columns="product_id", values="v", fill_value=0
    )


def percentage_without_recs(recs, basket_test):
    test_items = set(basket_test.columns)
    no_rec = [item for item in test_items if item not in recs]
    return 100 * len(no_rec) / len(test_items), no_rec


def save_scores(filename, matrix, product_ids, model_name):
    matrix = np.nan_to_num(matrix)
    np.fill_diagonal(matrix, 0)
    ids = np.array(product_ids)
    id_to_idx = {p: i for i, p in enumerate(ids)}
    with open(filename, "wb") as f:
        pickle.dump({
            "scores_matrix": matrix.astype(np.float32),
            "product_ids": ids,
            "id_to_idx": id_to_idx,
            "model": model_name,
        }, f)


def main():
    print("=" * 60, "\nTRAINING MODELS\n", "=" * 60)
    ok, info = test_connection("train")
    if not ok:
        print(f"Connection failed — {info}")
        return
    print(f"Connected to Train DB — {info}")
    engine = get_engine("train")
    orders = pd.read_sql("""
    SELECT DISTINCT
        opl.order_id,
        opl.product_id,
        opl.product_qty AS prod_qty,
        COALESCE(os.customer_id, opl.customer_id) AS customer_id,
        opl.date_created AS dt,
        COALESCE(os.status, 'wc-pending') AS status
    FROM wp_wc_order_product_lookup opl
    LEFT JOIN wp_wc_order_stats os 
        ON opl.order_id = os.order_id
    WHERE opl.order_id IS NOT NULL
    AND opl.product_id IS NOT NULL
    AND opl.product_qty > 0
    AND os.status = 'wc-processing';
    """, engine)
    print(f"Loaded {len(orders)} rows")
    orders_train = orders
    orders_test = orders
    print(f"Train rows: {len(orders_train)}")
    print(f"Test rows: {len(orders_test)}")
    basket_test = build_basket(orders_test)

    print("\nTraining models...")
    models = {
        "co": model_cooccurrence,
        "cos": model_cosine,
        "gc": lambda o, K=K: model_generalized_cosine(o, K, alpha=ALPHA),
        "lift": model_lift,
        "pmi": model_pmi,
        "hybrid": lambda o, K=K: model_hybrid(o, K, ALPHA, LAM),
    }
    recs = {name: fn(orders_train, K) for name, fn in models.items()}
    for name, r in recs.items():
        print(f"✓ {name} {len(r)}")

    percent, no_rec_items = percentage_without_recs(recs["co"], basket_test)
    print("\nItems without recommendations:")
    print(f"{percent:.2f}%")
    print(no_rec_items[:20])

    print("\nSaving recommendation dictionaries...")
    for name, data in recs.items():
        fname = f"../pkl_files/recs_{name}.pkl"
        with open(fname, "wb") as f:
            pickle.dump(data, f)
        print(f"✓ {fname}")

    print("\nBuilding matrices...")
    X, product_ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray().astype(float)
    freq = np.diag(co)
    N = X.shape[0]
    print("\nComputing score matrices...")
    save_scores("../pkl_files/scores_co.pkl", co, product_ids, "co")
    norm = np.sqrt(freq + eps)
    save_scores("../pkl_files/scores_cos.pkl", co / norm[:, None] / norm[None, :], product_ids, "cosine")
    denom = np.power(freq + eps, ALPHA)
    save_scores("../pkl_files/scores_gc.pkl", co / denom[:, None] / denom[None, :], product_ids, "g_cosine")
    save_scores("../pkl_files/scores_lift.pkl", (co * N) / ((freq[:, None] * freq[None, :]) + eps), product_ids, "lift")
    p_ij = co / N
    p_i = freq / N
    scores_pmi = np.log((p_ij + eps) / ((p_i[:, None] * p_i[None, :]) + eps))
    save_scores("../pkl_files/scores_pmi.pkl", np.maximum(scores_pmi, 0), product_ids, "pmi")
    popularity = freq / (freq.max() + eps)
    pop_matrix = np.tile(popularity, (len(popularity), 1))
    save_scores("../pkl_files/scores_hybrid.pkl", LAM * (co / denom[:, None] / denom[None, :]) + (1 - LAM) * pop_matrix, product_ids, "hybrid")
    print("\n", "=" * 60, "\nTRAINING COMPLETED\n", "=" * 60)


if __name__ == "__main__":
    main()