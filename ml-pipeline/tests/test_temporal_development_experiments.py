"""Testes do executor retomável de experimentos temporais."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.data.expanding_temporal_folds import materialize_expanding_temporal_folds
from src.training.temporal_development_experiments import (
    prepare_experiment_fold_caches,
    run_development_experiments,
)


def _raw_partition(
    split: str, *, start_id: int, start_time: int, rows: int
) -> pd.DataFrame:
    rng = np.random.default_rng(42 + start_id)
    signal = np.where(np.arange(rows) % 2, 2.0, -2.0) + rng.normal(0, 0.1, rows)
    label = (signal > 0).astype(np.int8)
    return pd.DataFrame(
        {
            "record_id": np.arange(start_id, start_id + rows),
            "srcip": ["10.0.0.1"] * rows,
            "sport": ["80"] * rows,
            "dstip": ["10.0.0.2"] * rows,
            "dsport": ["443"] * rows,
            "proto": np.where(label, "tcp", "udp"),
            "state": np.where(label, "FIN", "CON"),
            "service": np.where(label, "http", "dns"),
            "signal": signal,
            "noise": rng.normal(size=rows),
            "Stime": np.arange(start_time, start_time + rows),
            "Ltime": np.arange(start_time, start_time + rows),
            "attack_cat": np.where(label, "DoS", "BENIGN"),
            "label": label,
            "source_file": [f"{split}.parquet"] * rows,
            "Binary_Label": label,
            "temporal_session": [0 if split == "train" else 1] * rows,
            "split": [split] * rows,
        }
    )


def test_prepare_and_run_decision_tree_variants_without_test(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    fold_dir = tmp_path / "folds"
    cache_dir = tmp_path / "cache"
    report_dir = tmp_path / "reports"
    raw_dir.mkdir()
    _raw_partition("train", start_id=0, start_time=100, rows=80).to_parquet(
        raw_dir / "train.parquet", index=False
    )
    _raw_partition("validation", start_id=100, start_time=1_000, rows=20).to_parquet(
        raw_dir / "validation.parquet", index=False
    )
    _raw_partition("test", start_id=200, start_time=2_000, rows=20).to_parquet(
        raw_dir / "test.parquet", index=False
    )
    materialize_expanding_temporal_folds(
        input_dir=raw_dir,
        output_dir=fold_dir,
        report_path=tmp_path / "fold_audit.json",
        n_folds=3,
        window_size=3,
    )

    audits = prepare_experiment_fold_caches(
        raw_dir=raw_dir,
        fold_dir=fold_dir,
        cache_dir=cache_dir,
        report_dir=report_dir,
        selector_n_estimators=5,
        selector_n_jobs=1,
    )
    summary = run_development_experiments(
        cache_dir=cache_dir,
        report_dir=report_dir,
        algorithms=["decision_tree"],
        variants=["all", "top_2"],
        folds=[1, 2, 3],
        window_size=3,
        batch_size=7,
    )

    assert len(audits) == 3
    assert all(audit["fit_partition"] == "train" for audit in audits)
    assert summary["test_used"] is False
    assert summary["complete_configurations"] == 2
    assert (report_dir / "comparison_metrics.csv").exists()
    assert not (cache_dir / "test.parquet").exists()
    for row in summary["rows"]:
        assert "pr_auc_mean" in row
        assert row["folds"] == 3
