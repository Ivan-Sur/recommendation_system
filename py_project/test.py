import os, pickle
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from db import test_connection, get_engine

load_dotenv()
K = int(os.getenv("K", "5"))
DT_SPLIT = os.getenv("DT_SPLIT", "2026-02-06 11:22:08")


def evaluate(recs, basket_test, K):
    recalls, hits, precisions, aps = [], [], [], []
    for _, row in basket_test.iterrows():
        items = row[row > 0].index.tolist()
        if len(items) < 2:
            continue
        for seed in items:
            true_items = set(items) - {seed}
            if seed not in recs:
                continue
            recommended = recs[seed][:K]
            inter = set(recommended) & true_items
            hits.append(int(bool(inter)))
            recalls.append(len(inter) / len(true_items))
            precisions.append(len(inter) / K)
            running = 0
            psum = 0
            for i, item in enumerate(recommended):
                if item in true_items:
                    running += 1
                    psum += running / (i + 1)
            aps.append(psum / len(true_items))
    return {
        "Recall@K": np.mean(recalls),
        "HitRate@K": np.mean(hits),
        "Precision@K": np.mean(precisions),
        "MAP@K": np.mean(aps),
    }


def print_results(results, title="Results"):
    print(f"\n{title}\n" + "-" * 70)
    metrics = [
        "Recall@K",
        "HitRate@K",
        "Precision@K",
        "MAP@K",
    ]
    print(f"{'Model':<15}" + "".join(f"{m:<15}" for m in metrics))
    print("-" * 70)
    for method, data in results.items():
        print(
            f"{method:<15}" + "".join(f"{data.get(m,0):<15.4f}" for m in metrics)
        )
    print("-" * 70 + "\n")


def build_basket_matrix(orders):
    return orders.assign(v=1).pivot_table(
        index="order_id", columns="product_id", values="v", fill_value=0
    )


def run_test():
    print("=" * 60, "\nTESTING MODELS\n", "=" * 60)
    ok, info = test_connection("test")
    if not ok:
        print(f"Connection failed — {info}")
        return
    print(f"Connected to Test DB — {info}")
    engine = get_engine("test")
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
    print(f"Loaded {len(orders)} orders")
    orders["dt"] = pd.to_datetime(orders["dt"])
    print("\nLoading saved recommendations...")
    recs = {}
    files = {
        "occurrence": "../pkl_files/recs_co.pkl",
        "cosine": "../pkl_files/recs_cos.pkl",
        "g_cosine": "../pkl_files/recs_gc.pkl",
        "lift": "../pkl_files/recs_lift.pkl",
        "pmi": "../pkl_files/recs_pmi.pkl",
        "hybrid": "../pkl_files/recs_hybrid.pkl",
    }
    for name, f in files.items():
        try:
            with open(f, "rb") as fh:
                recs[name] = pickle.load(fh)
            print(f"✓ {name:<15} ({f})")
        except FileNotFoundError:
            print(f"✗ {name:<15} — File not found: {f}")
            return
    print("\n" + "=" * 60 + "\nEvaluation on ALL ORDERS\n" + "=" * 60)
    basket_all = build_basket_matrix(orders)
    print(f"Basket matrix: {basket_all.shape}")
    results_all = {name: evaluate(r, basket_all, K) for name, r in recs.items()}
    print_results(results_all, "Evaluation on ALL ORDERS")
    print("=" * 60)
    print(f"Evaluation on ORDERS AFTER {DT_SPLIT}")
    print("=" * 60)
    orders_after = orders[orders["dt"] >= pd.to_datetime(DT_SPLIT)]
    print(f"Found {len(orders_after)} orders after split")
    basket_after = build_basket_matrix(orders_after)
    print(f"Basket matrix: {basket_after.shape}")
    results_after = {name: evaluate(r, basket_after, K) for name, r in recs.items()}
    print_results(results_after, f"Evaluation on ORDERS AFTER {DT_SPLIT}")
    print("=" * 60)


if __name__ == "__main__":
    run_test()
