"""
Generate recommendations.sql based on model specified by BEST_RECS in .env
"""

import os, pickle
import numpy as np
from dotenv import load_dotenv

load_dotenv()
BEST_RECS = os.getenv("BEST_RECS", "co")
K = int(os.getenv("K", "5"))


def export_recommendations_sql(recs, scores_data, K, filename):
    scores = scores_data["scores_matrix"]
    ids = scores_data["product_ids"]
    id_to_idx = scores_data["id_to_idx"]

    # popularity order for fallback
    popularity = scores.sum(axis=0)
    pop_idx = np.argsort(popularity)[::-1]
    top_pop = [ids[i] for i in pop_idx]

    rows = []
    for item, rec_list in recs.items():
        if item not in id_to_idx:
            continue
        i = id_to_idx[item]
        rank = 1
        used = set()
        for rec in rec_list:
            if rec not in id_to_idx:
                continue
            j = id_to_idx[rec]
            score = float(scores[i, j])
            if score <= 0.1:
                continue
            rows.append(f"({item},{rec},{rank},{round(score,6)})")
            used.add(rec); rank += 1
            if rank > K:
                break
        # fallback popular items
        if rank <= K:
            for pop in top_pop:
                if pop == item or pop in used:
                    continue
                score = float(popularity[id_to_idx[pop]])
                rows.append(f"({item},{pop},{rank},{round(score,6)})")
                rank += 1
                if rank > K:
                    break
    # global fallback (-1)
    for rank, pop in enumerate(top_pop[:K], start=1):
        score = float(popularity[id_to_idx[pop]])
        rows.append(f"(-1,{pop},{rank},{round(score,6)})")

    # write SQL file
    with open(filename, "w", encoding="utf-8") as f:
        f.write("-- Generated recommendations SQL\n")
        f.write(f"-- Model: {BEST_RECS}\n")
        f.write(f"-- Items: {len(recs)}\n\n")
        f.write("DROP TABLE IF EXISTS recommendations;\n\n")
        f.write("""CREATE TABLE recommendations (
    item_id INT,
    recommended_id INT,
    rank_item INT,
    score FLOAT
);

""")
        f.write(
            "INSERT INTO recommendations (item_id, recommended_id, rank_item, score) VALUES\n"
        )
        f.write(",\n".join(rows))
        f.write(";\n")


def save_recommendations_to_sql():
    print("=" * 60, "\nSAVING RECOMMENDATIONS TO SQL\n", "=" * 60)
    pkl_recs = f"../pkl_files/recs_{BEST_RECS.replace('-', '_')}.pkl"
    pkl_scores = f"../pkl_files/scores_{BEST_RECS.replace('-', '_')}.pkl"
    try:
        with open(pkl_recs, "rb") as f:
            recs = pickle.load(f)
        print(f"✓ Loaded {len(recs)} items")
    except FileNotFoundError:
        print("Recommendations file not found")
        return
    try:
        with open(pkl_scores, "rb") as f:
            scores_data = pickle.load(f)
        print("✓ Scores loaded")
    except FileNotFoundError:
        print("Scores file not found")
        return
    export_recommendations_sql(recs, scores_data, K, "../sql_scripts/recommendations.sql")
    print("\n✓ recommendations.sql created")


if __name__ == "__main__":
    save_recommendations_to_sql()