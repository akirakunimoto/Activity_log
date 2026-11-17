from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from activity_log.storage import (
    DEFAULT_DB_PATH,
    DailyRecord,
    add_run,
    add_strength_sets,
    delete_run,
    delete_strength_set,
    get_daily_record,
    get_history,
    init_db,
    list_runs,
    list_strength_sets,
    save_daily_record,
)


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "activity.sqlite3"
        init_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_database_is_in_workspace_root(self) -> None:
        expected_path = Path(__file__).resolve().parents[1] / "activity.sqlite3"
        self.assertEqual(DEFAULT_DB_PATH, expected_path)

    def test_daily_record_upsert_and_ring_validation(self) -> None:
        record_date = date(2026, 11, 17)
        save_daily_record(
            DailyRecord(
                activity_date=record_date,
                sleep_score=82,
                steps=7000,
                move_kcal=350,
                move_goal_kcal=400,
                note="morning run",
            ),
            self.db_path,
        )
        save_daily_record(
            DailyRecord(activity_date=record_date, sleep_score=91),
            self.db_path,
        )

        saved = get_daily_record(record_date, self.db_path)
        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved.sleep_score, 91)
        self.assertIsNone(saved.move_kcal)

        with self.assertRaisesRegex(ValueError, "実績値と目標値"):
            save_daily_record(
                DailyRecord(
                    activity_date=record_date,
                    move_kcal=200,
                ),
                self.db_path,
            )

    def test_runs_and_strength_sets_are_saved_and_deletable(self) -> None:
        record_date = date(2026, 11, 17)
        first_run = add_run(record_date, 5.0, 25.0, self.db_path)
        second_run = add_run(record_date, 3.0, 18.0, self.db_path)
        self.assertEqual(len(list_runs(record_date, self.db_path)), 2)

        count = add_strength_sets(
            record_date,
            [
                {"exercise": "Squat", "weight_kg": 40, "repetitions": 10},
                {"exercise": "Squat", "weight_kg": 45, "repetitions": 8},
            ],
            self.db_path,
        )
        sets = list_strength_sets(record_date, self.db_path)
        self.assertEqual(count, 2)
        self.assertEqual(len(sets), 2)

        history = get_history(record_date, record_date, self.db_path)
        self.assertEqual(history[0].run_distance_km, 8.0)
        self.assertEqual(history[0].run_duration_minutes, 43.0)
        self.assertEqual(history[0].strength_set_count, 2)
        self.assertEqual(history[0].strength_volume_kg_reps, 760.0)

        self.assertTrue(delete_run(first_run, self.db_path))
        self.assertFalse(delete_run(first_run, self.db_path))
        self.assertTrue(delete_strength_set(sets[0].id, self.db_path))
        self.assertEqual(len(list_runs(record_date, self.db_path)), 1)
        self.assertEqual(len(list_strength_sets(record_date, self.db_path)), 1)
        self.assertNotEqual(first_run, second_run)

    def test_history_rejects_reversed_date_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "開始日は終了日より前"):
            get_history(date(2026, 11, 18), date(2026, 11, 17), self.db_path)


if __name__ == "__main__":
    unittest.main()
