from datetime import date
import unittest

from activity_log.analytics import (
    format_duration,
    format_pace,
    pace_minutes_per_km,
    summarize_history,
)
from activity_log.storage import HistoryRecord


class AnalyticsTests(unittest.TestCase):
    def test_pace_and_duration_formatting(self) -> None:
        self.assertEqual(pace_minutes_per_km(30, 10), 3)
        self.assertIsNone(pace_minutes_per_km(30, 0))
        self.assertEqual(format_pace(30 * 60, 10), "3:00 min/km")
        self.assertEqual(format_duration(75), "1時間15分")
        self.assertEqual(format_duration(42), "42分")

    def test_weekly_summary_uses_totals_and_ring_completion_ratio(self) -> None:
        summary = summarize_history(
            [
                HistoryRecord(
                    activity_date=date(2026, 11, 16),
                    sleep_score=80,
                    steps=5000,
                    floors_climbed=3,
                    move_kcal=300,
                    move_goal_kcal=400,
                    exercise_minutes=30,
                    exercise_goal_minutes=30,
                    stand_hours=8,
                    stand_goal_hours=10,
                    strength_minutes=40,
                    run_distance_km=5,
                    run_duration_minutes=25,
                    strength_set_count=4,
                    strength_volume_kg_reps=800,
                ),
                HistoryRecord(
                    activity_date=date(2026, 11, 17),
                    sleep_score=90,
                    steps=7000,
                    floors_climbed=5,
                    move_kcal=500,
                    move_goal_kcal=500,
                    exercise_minutes=20,
                    exercise_goal_minutes=40,
                    stand_hours=10,
                    stand_goal_hours=10,
                    strength_minutes=None,
                    run_distance_km=3,
                    run_duration_minutes=18,
                    strength_set_count=0,
                    strength_volume_kg_reps=0,
                ),
            ],
            "週",
        )
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary.loc[0, "steps"], 12000)
        self.assertEqual(summary.loc[0, "sleep_score"], 85)
        self.assertEqual(summary.loc[0, "run_pace_minutes_per_km"], 43 / 8)
        self.assertEqual(summary.loc[0, "move_progress_pct"], 800 / 900 * 100)
        self.assertAlmostEqual(summary.loc[0, "exercise_progress_pct"], 50 / 70 * 100)


if __name__ == "__main__":
    unittest.main()
