"""Métricas científicas usadas."""
from __future__ import annotations

from typing import Iterable

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

METRIC_NAMES = ("f1", "pr_auc", "auc_roc", "precision", "recall", "fpr")


def calculate_binary_metrics(
    y_true: Iterable[int],
    y_pred: Iterable[int],
    y_score: Iterable[float] | None = None,
) -> dict[str, float]:
    """Calcula F1, AUC-ROC, Precision, Recall e FPR para classificação binária."""
    true = np.asarray(list(y_true), dtype=int)
    pred = np.asarray(list(y_pred), dtype=int)
    score = np.asarray(list(y_score), dtype=float) if y_score is not None else pred

    tn, fp, _fn, _tp = confusion_matrix(true, pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    try:
        auc_roc = float(roc_auc_score(true, score))
    except ValueError:
        auc_roc = float("nan")
    try:
        pr_auc = float(average_precision_score(true, score))
    except ValueError:
        pr_auc = float("nan")

    return {
        "f1": float(f1_score(true, pred, zero_division=0)),
        "pr_auc": pr_auc,
        "auc_roc": auc_roc,
        "precision": float(precision_score(true, pred, zero_division=0)),
        "recall": float(recall_score(true, pred, zero_division=0)),
        "fpr": float(fpr),
    }


def summarize_fold_metrics(
    fold_metrics: list[dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Agrega métricas por média e desvio padrão entre folds."""
    summary: dict[str, dict[str, float]] = {}
    for metric_name in METRIC_NAMES:
        values = np.asarray([fold[metric_name] for fold in fold_metrics], dtype=float)
        summary[metric_name] = {
            "mean": float(np.nanmean(values)),
            "std": float(np.nanstd(values, ddof=0)),
        }
    return summary


def format_mean_std(metric: dict[str, float]) -> str:
    """Formata métrica como média +/- desvio padrão para relatório."""
    return f"{metric['mean']:.4f} +/- {metric['std']:.4f}"
