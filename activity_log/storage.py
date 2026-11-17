from __future__ import annotations

import math
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Generator, Iterable, Mapping

DatabasePath = str | Path
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "activity.sqlite3"


@dataclass(frozen=True)
class DailyRecord:
    activity_date: date
    sleep_score: int | None = None
    steps: int | None = None
    floors_climbed: int | None = None
    move_kcal: float | None = None
    move_goal_kcal: float | None = None
    exercise_minutes: float | None = None
    exercise_goal_minutes: float | None = None
    stand_hours: float | None = None
    stand_goal_hours: float | None = None
    strength_minutes: float | None = None
    note: str = ""


@dataclass(frozen=True)
class RunSession:
    id: int
    distance_km: float
    duration_seconds: int


@dataclass(frozen=True)
class StrengthSet:
    id: int
    exercise: str
    weight_kg: float
    repetitions: int


@dataclass(frozen=True)
class HistoryRecord:
    activity_date: date
    sleep_score: int | None
    steps: int | None
    floors_climbed: int | None
    move_kcal: float | None
    move_goal_kcal: float | None
    exercise_minutes: float | None
    exercise_goal_minutes: float | None
    stand_hours: float | None
    stand_goal_hours: float | None
    strength_minutes: float | None
    run_distance_km: float
    run_duration_minutes: float
    strength_set_count: int
    strength_volume_kg_reps: float


@contextmanager
def _connection(db_path: DatabasePath) -> Generator[sqlite3.Connection, None, None]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection


def init_db(db_path: DatabasePath = DEFAULT_DB_PATH) -> None:
    with _connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS daily_logs (
                activity_date TEXT PRIMARY KEY,
                sleep_score INTEGER CHECK (sleep_score BETWEEN 0 AND 100),
                steps INTEGER CHECK (steps >= 0),
                floors_climbed INTEGER CHECK (floors_climbed >= 0),
                move_kcal REAL CHECK (move_kcal >= 0),
                move_goal_kcal REAL CHECK (move_goal_kcal > 0),
                exercise_minutes REAL CHECK (exercise_minutes >= 0),
                exercise_goal_minutes REAL CHECK (exercise_goal_minutes > 0),
                stand_hours REAL CHECK (stand_hours >= 0),
                stand_goal_hours REAL CHECK (stand_goal_hours > 0),
                strength_minutes REAL CHECK (strength_minutes >= 0),
                note TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS running_sessions (
                id INTEGER PRIMARY KEY,
                activity_date TEXT NOT NULL
                    REFERENCES daily_logs(activity_date) ON DELETE CASCADE,
                distance_km REAL NOT NULL CHECK (distance_km > 0),
                duration_seconds INTEGER NOT NULL CHECK (duration_seconds > 0)
            );
            CREATE TABLE IF NOT EXISTS strength_sets (
                id INTEGER PRIMARY KEY,
                activity_date TEXT NOT NULL
                    REFERENCES daily_logs(activity_date) ON DELETE CASCADE,
                exercise TEXT NOT NULL,
                weight_kg REAL NOT NULL CHECK (weight_kg >= 0),
                repetitions INTEGER NOT NULL CHECK (repetitions > 0)
            );
            CREATE INDEX IF NOT EXISTS idx_runs_date
                ON running_sessions(activity_date);
            CREATE INDEX IF NOT EXISTS idx_strength_sets_date
                ON strength_sets(activity_date);
            """
        )


def _validate_daily_record(record: DailyRecord) -> None:
    if record.sleep_score is not None and not 0 <= record.sleep_score <= 100:
        raise ValueError("睡眠スコアは0〜100で入力してください。")
    if record.steps is not None and record.steps < 0:
        raise ValueError("歩数は0以上で入力してください。")
    if record.floors_climbed is not None and record.floors_climbed < 0:
        raise ValueError("登った階数は0以上で入力してください。")
    if record.strength_minutes is not None and record.strength_minutes < 0:
        raise ValueError("筋トレ時間は0以上で入力してください。")

    for label, actual, goal in (
        ("ムーブ", record.move_kcal, record.move_goal_kcal),
        ("エクササイズ", record.exercise_minutes, record.exercise_goal_minutes),
        ("スタンド", record.stand_hours, record.stand_goal_hours),
    ):
        if (actual is None) != (goal is None):
            raise ValueError(f"{label}は実績値と目標値を両方入力してください。")
        if actual is not None and (not math.isfinite(actual) or actual < 0):
            raise ValueError(f"{label}の実績値は0以上で入力してください。")
        if goal is not None and (not math.isfinite(goal) or goal <= 0):
            raise ValueError(f"{label}の目標値は0より大きく入力してください。")
    if record.strength_minutes is not None and not math.isfinite(
        record.strength_minutes
    ):
        raise ValueError("筋トレ時間は有限の数値で入力してください。")


def save_daily_record(
    record: DailyRecord, db_path: DatabasePath = DEFAULT_DB_PATH
) -> None:
    _validate_daily_record(record)
    with _connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO daily_logs (
                activity_date, sleep_score, steps, floors_climbed,
                move_kcal, move_goal_kcal,
                exercise_minutes, exercise_goal_minutes,
                stand_hours, stand_goal_hours, strength_minutes, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(activity_date) DO UPDATE SET
                sleep_score = excluded.sleep_score,
                steps = excluded.steps,
                floors_climbed = excluded.floors_climbed,
                move_kcal = excluded.move_kcal,
                move_goal_kcal = excluded.move_goal_kcal,
                exercise_minutes = excluded.exercise_minutes,
                exercise_goal_minutes = excluded.exercise_goal_minutes,
                stand_hours = excluded.stand_hours,
                stand_goal_hours = excluded.stand_goal_hours,
                strength_minutes = excluded.strength_minutes,
                note = excluded.note
            """,
            (
                record.activity_date.isoformat(),
                record.sleep_score,
                record.steps,
                record.floors_climbed,
                record.move_kcal,
                record.move_goal_kcal,
                record.exercise_minutes,
                record.exercise_goal_minutes,
                record.stand_hours,
                record.stand_goal_hours,
                record.strength_minutes,
                record.note,
            ),
        )


def get_daily_record(
    activity_date: date, db_path: DatabasePath = DEFAULT_DB_PATH
) -> DailyRecord | None:
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM daily_logs WHERE activity_date = ?",
            (activity_date.isoformat(),),
        ).fetchone()
    if row is None:
        return None
    return DailyRecord(
        activity_date=date.fromisoformat(str(row["activity_date"])),
        sleep_score=_optional_int(row["sleep_score"]),
        steps=_optional_int(row["steps"]),
        floors_climbed=_optional_int(row["floors_climbed"]),
        move_kcal=_optional_float(row["move_kcal"]),
        move_goal_kcal=_optional_float(row["move_goal_kcal"]),
        exercise_minutes=_optional_float(row["exercise_minutes"]),
        exercise_goal_minutes=_optional_float(row["exercise_goal_minutes"]),
        stand_hours=_optional_float(row["stand_hours"]),
        stand_goal_hours=_optional_float(row["stand_goal_hours"]),
        strength_minutes=_optional_float(row["strength_minutes"]),
        note=str(row["note"]),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise TypeError("データベースの整数値が不正です。")


def _required_int(value: object) -> int:
    if isinstance(value, int):
        return value
    raise TypeError("データベースの整数値が不正です。")


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError("データベースの数値が不正です。")


def _required_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError("データベースの数値が不正です。")


def _ensure_day(connection: sqlite3.Connection, activity_date: date) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO daily_logs (activity_date) VALUES (?)",
        (activity_date.isoformat(),),
    )


def add_run(
    activity_date: date,
    distance_km: float,
    duration_minutes: float,
    db_path: DatabasePath = DEFAULT_DB_PATH,
) -> int:
    if not math.isfinite(distance_km) or distance_km <= 0:
        raise ValueError("ランニング距離は0より大きく入力してください。")
    if not math.isfinite(duration_minutes) or duration_minutes <= 0:
        raise ValueError("ランニング時間は0より大きく入力してください。")
    duration_seconds = round(duration_minutes * 60)
    if duration_seconds <= 0:
        raise ValueError("ランニング時間は1秒以上で入力してください。")

    with _connection(db_path) as connection:
        _ensure_day(connection, activity_date)
        cursor = connection.execute(
            """
            INSERT INTO running_sessions
                (activity_date, distance_km, duration_seconds)
            VALUES (?, ?, ?)
            """,
            (activity_date.isoformat(), distance_km, duration_seconds),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("ランニング記録のIDを取得できませんでした。")
        return cursor.lastrowid


def list_runs(
    activity_date: date, db_path: DatabasePath = DEFAULT_DB_PATH
) -> list[RunSession]:
    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, distance_km, duration_seconds
            FROM running_sessions
            WHERE activity_date = ?
            ORDER BY id
            """,
            (activity_date.isoformat(),),
        ).fetchall()
    return [
        RunSession(
            id=int(row["id"]),
            distance_km=float(row["distance_km"]),
            duration_seconds=int(row["duration_seconds"]),
        )
        for row in rows
    ]


def delete_run(run_id: int, db_path: DatabasePath = DEFAULT_DB_PATH) -> bool:
    with _connection(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM running_sessions WHERE id = ?", (run_id,)
        )
        return cursor.rowcount > 0


def add_strength_sets(
    activity_date: date,
    sets: Iterable[Mapping[str, object]],
    db_path: DatabasePath = DEFAULT_DB_PATH,
) -> int:
    normalized: list[tuple[str, float, int]] = []
    for strength_set in sets:
        exercise_value = strength_set.get("exercise")
        weight_value = strength_set.get("weight_kg")
        repetitions_value = strength_set.get("repetitions")
        if (
            exercise_value is None
            and weight_value is None
            and repetitions_value is None
        ):
            continue
        if not isinstance(exercise_value, str) or not exercise_value.strip():
            raise ValueError("筋トレの種目を入力してください。")
        if not isinstance(weight_value, (int, float)) or isinstance(
            weight_value, bool
        ):
            raise ValueError("筋トレの重量を入力してください。")
        if not isinstance(repetitions_value, (int, float)) or isinstance(
            repetitions_value, bool
        ):
            raise ValueError("筋トレの回数を入力してください。")
        exercise = exercise_value.strip()
        weight = float(weight_value)
        repetitions_float = float(repetitions_value)
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("筋トレの重量は0以上で入力してください。")
        if (
            not math.isfinite(repetitions_float)
            or repetitions_float <= 0
            or not repetitions_float.is_integer()
        ):
            raise ValueError("筋トレの回数は1以上の整数で入力してください。")
        normalized.append((exercise, weight, int(repetitions_float)))

    if not normalized:
        raise ValueError("少なくとも1セットを入力してください。")

    with _connection(db_path) as connection:
        _ensure_day(connection, activity_date)
        connection.executemany(
            """
            INSERT INTO strength_sets
                (activity_date, exercise, weight_kg, repetitions)
            VALUES (?, ?, ?, ?)
            """,
            [
                (activity_date.isoformat(), exercise, weight, repetitions)
                for exercise, weight, repetitions in normalized
            ],
        )
    return len(normalized)


def list_strength_sets(
    activity_date: date, db_path: DatabasePath = DEFAULT_DB_PATH
) -> list[StrengthSet]:
    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, exercise, weight_kg, repetitions
            FROM strength_sets
            WHERE activity_date = ?
            ORDER BY id
            """,
            (activity_date.isoformat(),),
        ).fetchall()
    return [
        StrengthSet(
            id=int(row["id"]),
            exercise=str(row["exercise"]),
            weight_kg=float(row["weight_kg"]),
            repetitions=int(row["repetitions"]),
        )
        for row in rows
    ]


def delete_strength_set(
    set_id: int, db_path: DatabasePath = DEFAULT_DB_PATH
) -> bool:
    with _connection(db_path) as connection:
        cursor = connection.execute("DELETE FROM strength_sets WHERE id = ?", (set_id,))
        return cursor.rowcount > 0


def get_history(
    start_date: date,
    end_date: date,
    db_path: DatabasePath = DEFAULT_DB_PATH,
) -> list[HistoryRecord]:
    if start_date > end_date:
        raise ValueError("期間の開始日は終了日より前にしてください。")
    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                d.activity_date,
                d.sleep_score,
                d.steps,
                d.floors_climbed,
                d.move_kcal,
                d.move_goal_kcal,
                d.exercise_minutes,
                d.exercise_goal_minutes,
                d.stand_hours,
                d.stand_goal_hours,
                d.strength_minutes,
                COALESCE(r.distance_km, 0) AS run_distance_km,
                COALESCE(r.duration_minutes, 0) AS run_duration_minutes,
                COALESCE(s.set_count, 0) AS strength_set_count,
                COALESCE(s.volume_kg_reps, 0) AS strength_volume_kg_reps
            FROM daily_logs AS d
            LEFT JOIN (
                SELECT
                    activity_date,
                    SUM(distance_km) AS distance_km,
                    SUM(duration_seconds) / 60.0 AS duration_minutes
                FROM running_sessions
                GROUP BY activity_date
            ) AS r ON r.activity_date = d.activity_date
            LEFT JOIN (
                SELECT
                    activity_date,
                    COUNT(*) AS set_count,
                    SUM(weight_kg * repetitions) AS volume_kg_reps
                FROM strength_sets
                GROUP BY activity_date
            ) AS s ON s.activity_date = d.activity_date
            WHERE d.activity_date BETWEEN ? AND ?
            ORDER BY d.activity_date
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [
        HistoryRecord(
            activity_date=date.fromisoformat(str(row["activity_date"])),
            sleep_score=_optional_int(row["sleep_score"]),
            steps=_optional_int(row["steps"]),
            floors_climbed=_optional_int(row["floors_climbed"]),
            move_kcal=_optional_float(row["move_kcal"]),
            move_goal_kcal=_optional_float(row["move_goal_kcal"]),
            exercise_minutes=_optional_float(row["exercise_minutes"]),
            exercise_goal_minutes=_optional_float(row["exercise_goal_minutes"]),
            stand_hours=_optional_float(row["stand_hours"]),
            stand_goal_hours=_optional_float(row["stand_goal_hours"]),
            strength_minutes=_optional_float(row["strength_minutes"]),
            run_distance_km=_required_float(row["run_distance_km"]),
            run_duration_minutes=_required_float(row["run_duration_minutes"]),
            strength_set_count=_required_int(row["strength_set_count"]),
            strength_volume_kg_reps=_required_float(
                row["strength_volume_kg_reps"]
            ),
        )
        for row in rows
    ]
