"""
This module contains implementations of various product recommendation models based on co-occurrence and related metrics.
The models include: co-occurrence, cosine, generalized cosine, lift, pmi, and hybrid."""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix


# ---------------------------------------------------
# UTILITIES
# ---------------------------------------------------

def build_matrix(orders_train):

    basket = (
        orders_train
        .assign(v=1)
        .pivot_table(
            index="order_id",
            columns="product_id",
            values="v",
            fill_value=0
        )
    )

    X = csr_matrix(basket.values)

    product_ids = basket.columns.values

    product_to_idx = {p: i for i, p in enumerate(product_ids)}

    return X, product_ids, product_to_idx


def compute_cooccurrence(X):
    return (X.T @ X).astype(float)


def topk_from_matrix(matrix, product_ids, K):

    result = {}

    for i, item in enumerate(product_ids):
        scores = matrix[i].copy()
        scores[i] = -np.inf
        valid_idx = np.where(scores > 0.1)[0]
        if len(valid_idx) == 0: continue
        # сортируем только валидные
        sorted_idx = valid_idx[np.argsort(scores[valid_idx])[::-1]]
        top_idx = sorted_idx[:K]
        if len(top_idx) > 0:
            result[item] = product_ids[top_idx].tolist()
    return result


# ---------------------------------------------------
# CO-OCCURRENCE
# ---------------------------------------------------

def model_cooccurrence(orders_train, K):

    X, product_ids, _ = build_matrix(orders_train)

    co_matrix = compute_cooccurrence(X).toarray()

    return topk_from_matrix(co_matrix, product_ids, K)


# ---------------------------------------------------
# COSINE
# ---------------------------------------------------

def model_cosine(orders_train, K, eps=1e-9):

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray()

    freq = np.diag(co)

    norm = np.sqrt(freq + eps)

    cosine = co / norm[:, None] / norm[None, :]

    return topk_from_matrix(cosine, product_ids, K)


# ---------------------------------------------------
# GENERALIZED COSINE
# ---------------------------------------------------

def model_generalized_cosine(orders_train, K, alpha=1, eps=1e-9):

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray()

    freq = np.diag(co)

    score = co / np.power(freq + eps, alpha)[:, None]
    score = score / np.power(freq + eps, 1 - alpha)[None, :]

    return topk_from_matrix(score, product_ids, K)


# ---------------------------------------------------
# LIFT
# ---------------------------------------------------

def model_lift(orders_train, K, eps=1e-9):

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray()

    N = X.shape[0]

    freq = np.diag(co)

    lift = (co * N) / ((freq[:, None] * freq[None, :]) + eps)

    return topk_from_matrix(lift, product_ids, K)


# ---------------------------------------------------
# PMI
# ---------------------------------------------------

def model_pmi(orders_train, K, eps=1e-9):

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray()

    N = X.shape[0]

    freq = np.diag(co)

    p_ij = co / N
    p_i = freq / N

    pmi = np.log((p_ij + eps) / ((p_i[:, None] * p_i[None, :]) + eps))

    pmi[p_ij == 0] = 0

    return topk_from_matrix(pmi, product_ids, K)


# ---------------------------------------------------
# HYBRID
# ---------------------------------------------------

def model_hybrid(orders_train, K, alpha_gc=1.0, lam=0.7, eps=1e-9):

    X, product_ids, _ = build_matrix(orders_train)

    co = compute_cooccurrence(X).toarray()

    freq = np.diag(co)

    gcos = co / np.power(freq + eps, alpha_gc)[:, None]
    gcos /= np.power(freq + eps, 1 - alpha_gc)[None, :]

    popularity = freq / freq.max()

    hybrid = lam * gcos + (1 - lam) * popularity[None, :]

    return topk_from_matrix(hybrid, product_ids, K)