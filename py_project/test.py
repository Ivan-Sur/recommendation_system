import os
import pandas as pd
import numpy as np
import pickle
from dotenv import load_dotenv
from db import test_connection, get_engine

load_dotenv()

# Параметры из .env
K = int(os.getenv("K", "5"))
DT_SPLIT = os.getenv("DT_SPLIT", "2026-02-06 11:22:08")


# =============================
# EVALUATION FUNCTIONS
# =============================

def evaluate(recs, basket_test, K):
    """Оценить рекомендации метриками"""
    recalls, hits, precisions, aps = [], [], [], []

    for _, row in basket_test.iterrows():
        items = row[row > 0].index.tolist()

        if len(items) < 2:
            continue

        # пробегаем все товары как seed
        for seed in items:
            true_items = set(items)
            true_items.remove(seed)

            if seed not in recs:
                continue

            recommended = recs[seed][:K]
            recommended_set = set(recommended)
            intersection = recommended_set & true_items

            # hit
            hits.append(int(len(intersection) > 0))
            # recall
            recalls.append(len(intersection) / len(true_items))
            # precision
            precisions.append(len(intersection) / K)

            # Average Precision
            running_hits = 0
            precision_sum = 0
            for i, item in enumerate(recommended):
                if item in true_items:
                    running_hits += 1
                    precision_sum += running_hits / (i + 1)
            aps.append(precision_sum / len(true_items))

    return {
        "Recall@K": np.mean(recalls),
        "HitRate@K": np.mean(hits),
        "Precision@K": np.mean(precisions),
        "MAP@K": np.mean(aps)
    }


def print_results(results, title="Results"):
    """Вывести результаты в табличном формате"""
    print(f"\n{title}")
    print("-" * 70)
    metrics = ['Recall@K', 'HitRate@K', 'Precision@K', 'MAP@K']
    print(f"{'Model':<15}", end="")
    for metric in metrics:
        print(f"{metric:<15}", end="")
    print()
    print("-" * 70)
    for method, data in results.items():
        print(f"{method:<15}", end="")
        for metric in metrics:
            val = data.get(metric, 0)
            print(f"{val:<15.4f}", end="")
        print()
    print("-" * 70 + "\n")


def build_basket_matrix(orders):
    """Построить basket matrix из заказов"""
    basket = (
        orders
        .assign(v=1)
        .pivot_table(
            index="order_id",
            columns="product_id",
            values="v",
            fill_value=0
        )
    )
    return basket


# =============================
# MAIN TESTING LOGIC
# =============================

def run_test():
    print("=" * 60)
    print("TESTING MODELS")
    print("=" * 60)
    
    # Проверяем подключение к тестовой БД
    ok, info = test_connection("test")
    if not ok:
        print(f"Connection failed — {info}")
        return
    print(f"Connected to Test DB — {info}")

    # Подключаемся к БД
    engine = get_engine("test")

    # Читаем заказы из БД
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

    # Конвертим дату
    orders["dt"] = pd.to_datetime(orders["dt"])

    # Загружаем сохраненные рекомендации
    print("\nLoading saved recommendations...")
    recs = {}
    pkl_files = {
        "occurrence": "../pkl_files/recs_co.pkl",
        "cosine": "../pkl_files/recs_cos.pkl",
        "g_cosine": "../pkl_files/recs_gc.pkl",
        "lift": "../pkl_files/recs_lift.pkl",
        "pmi": "../pkl_files/recs_pmi.pkl",
        "hybrid": "../pkl_files/recs_hybrid.pkl",
    }

    for name, filename in pkl_files.items():
        try:
            with open(filename, "rb") as f:
                recs[name] = pickle.load(f)
                print(f"✓ {name:<15} ({filename})")
        except FileNotFoundError:
            print(f"✗ {name:<15} — File not found: {filename}")
            return

    # ===========================
    # Оценка на ВСЕЙ БД
    # ===========================
    print("\n" + "=" * 60)
    print("Evaluation on ALL ORDERS")
    print("=" * 60)

    basket_all = build_basket_matrix(orders)
    print(f"Basket matrix: {basket_all.shape}")

    results_all = {}
    for name, model_recs in recs.items():
        print(f"Evaluating {name}...", end=" ")
        results_all[name] = evaluate(model_recs, basket_all, K)
        print("✓")

    print_results(results_all, "Evaluation on ALL ORDERS")

    # ===========================
    # Оценка ПОСЛЕ DT_SPLIT
    # ===========================
    print("=" * 60)
    print(f"Evaluation on ORDERS AFTER {DT_SPLIT}")
    print("=" * 60)

    orders_after = orders[orders["dt"] >= pd.to_datetime(DT_SPLIT)]
    print(f"Found {len(orders_after)} orders after split")

    basket_after = build_basket_matrix(orders_after)
    print(f"Basket matrix: {basket_after.shape}")

    results_after = {}
    for name, model_recs in recs.items():
        print(f"Evaluating {name}...", end=" ")
        results_after[name] = evaluate(model_recs, basket_after, K)
        print("✓")

    print_results(results_after, f"Evaluation on ORDERS AFTER {DT_SPLIT}")

    print("=" * 60)
    print("Testing completed!")
    print("=" * 60)


# =============================
# ЗАПУСК
# =============================

if __name__ == "__main__":
    run_test()
