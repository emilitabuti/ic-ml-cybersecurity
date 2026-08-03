from src.training.metrics import calculate_binary_metrics, summarize_fold_metrics


def test_calculate_binary_metrics_includes_fpr() -> None:
    y_true = [0, 0, 1, 1]
    y_pred = [0, 1, 1, 0]
    y_score = [0.1, 0.8, 0.9, 0.2]

    metrics = calculate_binary_metrics(y_true, y_pred, y_score)

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["fpr"] == 0.5
    assert metrics["auc_roc"] == 0.75
    assert metrics["pr_auc"] == 0.8333333333333333


def test_summarize_fold_metrics_returns_mean_and_std() -> None:
    summary = summarize_fold_metrics(
        [
            {"f1": 0.8, "pr_auc": 0.85, "auc_roc": 0.9, "precision": 0.7, "recall": 1.0, "fpr": 0.1},
            {"f1": 0.6, "pr_auc": 0.65, "auc_roc": 0.7, "precision": 0.9, "recall": 0.5, "fpr": 0.3},
        ]
    )

    assert summary["f1"]["mean"] == 0.7
    assert summary["f1"]["std"] == 0.10000000000000003
    assert summary["fpr"]["mean"] == 0.2
