"""
Training script for product recommendation models.
This script connects to the training database, loads order data, and trains several recommendation models based on 
co-occurrence and related metrics. The trained models are saved as pickled files for later use in generating recommendations."""

import os
import pandas as pd
import numpy as np
import pickle
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
    compute_cooccurrence
)

load_dotenv()

K = int(os.getenv("K", "5"))
ALPHA = float(os.getenv("ALPHA", "0.95"))
LAM = float(os.getenv("LAM", "0.8"))

eps = 1e-9


def build_basket(orders):
    return (
        orders
        .assign(v=1)
        .pivot_table(
            index="order_id",
            columns="product_id",
            values="v",
            fill_value=0
        )
    )


def percentage_without_recs(recs, basket_test):
    test_items = set(basket_test.columns)
    print('d') if 1187 in test_items else print('not1')
    print('d2') if 960 in test_items else print('not2')
    no_rec_items = [item for item in test_items if item not in recs]
    percent_no_rec = 100 * len(no_rec_items) / len(test_items)
    return percent_no_rec, no_rec_items


def save_scores(filename, matrix, product_ids, model_name):

    matrix = np.nan_to_num(matrix)
    np.fill_diagonal(matrix, 0)

    product_ids = np.array(product_ids)
    id_to_idx = {p: i for i, p in enumerate(product_ids)}

    with open(filename, "wb") as f:
        pickle.dump({
            "scores_matrix": matrix.astype(np.float32),
            "product_ids": product_ids,
            "id_to_idx": id_to_idx,
            "model": model_name
        }, f)


def main():

    print("=" * 60)
    print("TRAINING MODELS")
    print("=" * 60)

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

    # order_dates = (
    #     orders
    #     .groupby("order_id")["dt"]
    #     .min()
    #     .reset_index()
    # )

    # cutoff_date = order_dates["dt"].quantile(0.9)

    # train_orders_ids = order_dates[order_dates["dt"] <= cutoff_date]["order_id"]
    # test_orders_ids = order_dates[order_dates["dt"] > cutoff_date]["order_id"]

    orders_train = orders  #[orders["order_id"].isin(train_orders_ids)]
    orders_test = orders     #[orders["order_id"].isin(test_orders_ids)]

    print(f"Train rows: {len(orders_train)}")
    print(f"Test rows: {len(orders_test)}")

    basket_test = build_basket(orders_test)

    print("\nTraining models...")

    recs_co = model_cooccurrence(orders_train, K)
    recs_cos = model_cosine(orders_train, K)
    recs_gc = model_generalized_cosine(orders_train, K, alpha=ALPHA)
    recs_lift = model_lift(orders_train, K)
    recs_pmi = model_pmi(orders_train, K)
    recs_hybrid = model_hybrid(orders_train, K, ALPHA, LAM)

    print(f"✓ co-occurrence {len(recs_co)}")
    print(f"✓ cosine {len(recs_cos)}")
    print(f"✓ generalized cosine {len(recs_gc)}")
    print(f"✓ lift {len(recs_lift)}")
    print(f"✓ pmi {len(recs_pmi)}")
    print(f"✓ hybrid {len(recs_hybrid)}")

    percent, no_rec_items = percentage_without_recs(recs_co, basket_test)

    print("\nItems without recommendations:")
    print(f"{percent:.2f}%")
    print(no_rec_items[:20])

    print("\nSaving recommendation dictionaries...")

    rec_dicts = {
        "../pkl_files/recs_co.pkl": recs_co,
        "../pkl_files/recs_cos.pkl": recs_cos,
        "../pkl_files/recs_gc.pkl": recs_gc,
        "../pkl_files/recs_lift.pkl": recs_lift,
        "../pkl_files/recs_pmi.pkl": recs_pmi,
        "../pkl_files/recs_hybrid.pkl": recs_hybrid,
    }

    for name, data in rec_dicts.items():
        with open(name, "wb") as f:
            pickle.dump(data, f)
        print(f"✓ {name}")

    print("\nBuilding matrices...")

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray().astype(float)

    freq = np.diag(co)
    N = X.shape[0]

    print("\nComputing score matrices...")

    # CO
    scores_co = co.copy()
    save_scores("../pkl_files/scores_co.pkl", scores_co, product_ids, "co")

    # COSINE
    norm = np.sqrt(freq + eps)
    scores_cos = co / norm[:, None] / norm[None, :]
    save_scores("../pkl_files/scores_cos.pkl", scores_cos, product_ids, "cosine")

    # GENERALIZED COSINE
    denom = np.power(freq + eps, ALPHA)
    scores_gc = co / denom[:, None] / denom[None, :]
    save_scores("../pkl_files/scores_gc.pkl", scores_gc, product_ids, "g_cosine")

    # LIFT
    scores_lift = (co * N) / ((freq[:, None] * freq[None, :]) + eps)
    save_scores("../pkl_files/scores_lift.pkl", scores_lift, product_ids, "lift")

    # PMI -> PPMI
    p_ij = co / N
    p_i = freq / N

    scores_pmi = np.log((p_ij + eps) / ((p_i[:, None] * p_i[None, :]) + eps))
    scores_pmi = np.maximum(scores_pmi, 0)

    save_scores("../pkl_files/scores_pmi.pkl", scores_pmi, product_ids, "pmi")

    # HYBRID
    popularity = freq / (freq.max() + eps)
    pop_matrix = np.tile(popularity, (len(popularity), 1))

    scores_hybrid = LAM * scores_gc + (1 - LAM) * pop_matrix

    save_scores("../pkl_files/scores_hybrid.pkl", scores_hybrid, product_ids, "hybrid")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()