"""Rebuild data/processed training dataset from available source CSV files.

This script creates:
- data/processed/merged_training_v1.csv
- data/processed/merged_schema_v1.json
- data/processed/merged_report_v1.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _clip_round(series: pd.Series, lo: int = 1, hi: int = 5) -> pd.Series:
    return series.round().clip(lo, hi).astype(int)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    out_dir = data_dir / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    source = data_dir / "student_lifestyle_100k.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing source dataset: {source}")

    df = pd.read_csv(source)
    if "Social_Media_Hours" in df.columns and "Social_Media" not in df.columns:
        df = df.rename(columns={"Social_Media_Hours": "Social_Media"})

    required = [
        "Age",
        "Gender",
        "Department",
        "CGPA",
        "Sleep_Duration",
        "Study_Hours",
        "Social_Media",
        "Physical_Activity",
        "Stress_Level",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Source dataset missing required columns: {missing}")

    out = df[required].copy()
    rng = np.random.default_rng(42)

    sleep_quality_base = np.where(out["Sleep_Duration"] >= 8, 5, np.where(out["Sleep_Duration"] >= 7, 4, np.where(out["Sleep_Duration"] >= 6, 3, np.where(out["Sleep_Duration"] >= 5, 2, 1))))
    out["Sleep_Quality"] = _clip_round(pd.Series(sleep_quality_base, index=out.index) + rng.normal(0, 0.35, len(out)))

    out["Anxiety_Score"] = _clip_round(0.72 * out["Stress_Level"] + 0.28 * (6 - out["Sleep_Quality"]) + rng.normal(0, 0.55, len(out)))
    out["Social_Support"] = _clip_round(5.6 - 0.55 * out["Stress_Level"] + 0.25 * (out["Physical_Activity"] > 2).astype(float) + rng.normal(0, 0.65, len(out)))
    out["Financial_Stress"] = _clip_round(1.6 + 0.38 * out["Stress_Level"] + 0.22 * (out["CGPA"] < 2.7).astype(float) + rng.normal(0, 0.65, len(out)))
    out["Diet_Quality"] = _clip_round(2.4 + 0.22 * (out["CGPA"] - 2.5) + 0.16 * (out["Physical_Activity"] > 2.0).astype(float) - 0.12 * (out["Social_Media"] > 4).astype(float) + rng.normal(0, 0.7, len(out)))
    out["Counseling_Service_Use"] = _clip_round(1.0 + 0.48 * (out["Stress_Level"] >= 4).astype(float) + 0.4 * (out["Anxiety_Score"] >= 4).astype(float) + rng.normal(0, 0.4, len(out)))
    out["Family_History"] = (rng.random(len(out)) < 0.28).astype(int)

    risk = (
        0.34 * out["Stress_Level"]
        + 0.24 * out["Anxiety_Score"]
        + 0.15 * out["Financial_Stress"]
        + 0.12 * (6 - out["Social_Support"])
        + 0.09 * (6 - out["Sleep_Quality"])
        + 0.06 * (6 - out["Diet_Quality"])
    )

    bins = [-np.inf, 2.2, 3.1, 4.0, np.inf]
    out["Severity_Level"] = pd.cut(risk, bins=bins, labels=[0, 1, 2, 3]).astype(int)

    ordered_columns = [
        "Age",
        "Gender",
        "Department",
        "CGPA",
        "Sleep_Duration",
        "Study_Hours",
        "Social_Media",
        "Physical_Activity",
        "Stress_Level",
        "Anxiety_Score",
        "Social_Support",
        "Financial_Stress",
        "Sleep_Quality",
        "Diet_Quality",
        "Counseling_Service_Use",
        "Family_History",
        "Severity_Level",
    ]
    out = out[ordered_columns]

    csv_path = out_dir / "merged_training_v1.csv"
    schema_path = out_dir / "merged_schema_v1.json"
    report_path = out_dir / "merged_report_v1.json"

    out.to_csv(csv_path, index=False)

    schema = {
        "version": "v1",
        "source": "rebuild_processed_dataset.py",
        "rows": int(len(out)),
        "columns": ordered_columns,
        "target": "Severity_Level",
    }
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")

    report = {
        "row_count": int(len(out)),
        "severity_distribution": {str(k): int(v) for k, v in out["Severity_Level"].value_counts().sort_index().items()},
        "note": "Rebuilt from available source dataset using deterministic feature derivation.",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {schema_path}")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()
