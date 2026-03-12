"""
Models for product recommendation using co-occurrence
and related similarity metrics.
"""

import numpy as np
from scipy.sparse import csr_matrix

# --- utilities ---------------------------------------------------

def build_matrix(orders_train):
    """Build sparse order×product basket and index maps."""
    basket = orders_train.assign(v=1).pivot_table(
        index="order_id", columns="product_id", values="v", fill_value=0
    )
    X = csr_matrix(basket.values)
    ids = basket.columns.values
    return X, ids, {p: i for i, p in enumerate(ids)}


def compute_cooccurrence(X):
    """Return float co-occurrence matrix XᵀX."""
    return (X.T @ X).astype(float)


def topk_from_matrix(matrix, product_ids, K):
    """Select top‑K recommendations per item, ignore self/low scores."""
    result = {}
    for i, item in enumerate(product_ids):
        row = matrix[i].copy()
        row[i] = -np.inf
        if not (row > 0.1).any():
            continue
        idx = np.argsort(row)[::-1][:K]
        result[item] = product_ids[idx].tolist()
    return result

# --- models ------------------------------------------------------

def model_cooccurrence(orders_train, K):
    X, ids, _ = build_matrix(orders_train)
    mat = compute_cooccurrence(X).toarray()
    return topk_from_matrix(mat, ids, K)


def model_cosine(orders_train, K, eps=1e-9):
    X, ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray()
    freq = np.diag(co)
    norm = np.sqrt(freq + eps)
    cosine = co / norm[:, None] / norm[None, :]
    return topk_from_matrix(cosine, ids, K)


def model_generalized_cosine(orders_train, K, alpha=1, eps=1e-9):
    X, ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray()
    freq = np.diag(co)
    score = co / np.power(freq + eps, alpha)[:, None]
    score = score / np.power(freq + eps, 1 - alpha)[None, :]
    return topk_from_matrix(score, ids, K)


def model_lift(orders_train, K, eps=1e-9):
    X, ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray()
    N = X.shape[0]
    freq = np.diag(co)
    lift = (co * N) / ((freq[:, None] * freq[None, :]) + eps)
    return topk_from_matrix(lift, ids, K)


def model_pmi(orders_train, K, eps=1e-9):
    X, ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray()
    N = X.shape[0]
    freq = np.diag(co)
    p_ij = co / N
    p_i = freq / N
    pmi = np.log((p_ij + eps) / ((p_i[:, None] * p_i[None, :]) + eps))
    pmi[p_ij == 0] = 0
    return topk_from_matrix(pmi, ids, K)


def model_hybrid(orders_train, K, alpha_gc=1.0, lam=0.7, eps=1e-9):
    X, ids, _ = build_matrix(orders_train)
    co = compute_cooccurrence(X).toarray()
    freq = np.diag(co)
    gcos = co / np.power(freq + eps, alpha_gc)[:, None]
    gcos /= np.power(freq + eps, 1 - alpha_gc)[None, :]
    popularity = freq / freq.max()
    hybrid = lam * gcos + (1 - lam) * popularity[None, :]
    return topk_from_matrix(hybrid, ids, K)
