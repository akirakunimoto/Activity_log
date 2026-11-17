from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from activity_log.storage import HistoryRecord

def pace_minutes_per_km(duration_minutes: float, distance_km: float) -> float | None:
    if distance_km <= 0:
        return None
    return duration_minutes / distance_km


def format_pace(duration_seconds: int, distance_km: float) -> str:
    pace = pace_minutes_per_km(duration_seconds / 60, distance_km)
    if pace is None:
        return "—"
    total_seconds = round(pace * 60)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d} min/km"


def format_duration(total_minutes: float) -> str:
    total_seconds = round(total_minutes * 60)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}時間{minutes:02d}分"
    return f"{minutes}分"


def summarize_history(
    records: list[HistoryRecord], period: str
) -> pd.DataFrame:
    frame = pd.DataFrame([asdict(record) for record in records])
    if frame.empty:
        return frame

    frame["activity_date"] = pd.to_datetime(frame["activity_date"])
    frequency = {"日": "D", "週": "W-SUN", "月": "MS"}.get(period)
    if frequency is None:
        raise ValueError(f"未対応の集計単位です: {period}")

    if period == "日":
        summary = frame.set_index("activity_date").sort_index()
    else:
        aggregations: dict[str, str] = {
            "sleep_score": "mean",
            "steps": "sum",
            "floors_climbed": "sum",
            "move_kcal": "sum",
            "move_goal_kcal": "sum",
            "exercise_minutes": "sum",
            "exercise_goal_minutes": "sum",
            "stand_hours": "sum",
            "stand_goal_hours": "sum",
            "strength_minutes": "sum",
            "run_distance_km": "sum",
            "run_duration_minutes": "sum",
            "strength_set_count": "sum",
            "strength_volume_kg_reps": "sum",
        }
        summary = (
            frame.set_index("activity_date")
            .sort_index()
            .resample(frequency)
            .agg(aggregations)
        )

    summary["run_pace_minutes_per_km"] = (
        summary["run_duration_minutes"]
        .div(summary["run_distance_km"].where(summary["run_distance_km"] > 0))
    )
    for actual, goal, progress in (
        ("move_kcal", "move_goal_kcal", "move_progress_pct"),
        ("exercise_minutes", "exercise_goal_minutes", "exercise_progress_pct"),
        ("stand_hours", "stand_goal_hours", "stand_progress_pct"),
    ):
        summary[progress] = (
            summary[actual].div(summary[goal].where(summary[goal] > 0)) * 100
        )
    return summary.reset_index()
