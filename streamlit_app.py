from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from activity_log.analytics import format_duration, format_pace, summarize_history
from activity_log.storage import (
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

TRAINING_EXERCISES = (
    "01_ショルダープレス",
    "02_チェストプレス",
    "03_ラットプルダウン",
    "04_バイセップスカール",
    "05_ディップス",
    "06_レッグプレス",
    "07_アダクション",
    "08_アブダクション",
    "09_アブドミナルトレーナー",
    "10_アブベンチ",
    "11_トレッドミル",
    "12_バイク",
)
DEFAULT_MOVE_GOAL_KCAL = 550.0
DEFAULT_EXERCISE_GOAL_MINUTES = 30.0
DEFAULT_STAND_GOAL_HOURS = 12.0


def _ring_goal_for_save(
    actual: float | None,
    goal: float | None,
    default_goal: float,
    saved_goal: float | None,
) -> float | None:
    if actual is None and saved_goal is None and goal == default_goal:
        return None
    return goal


st.set_page_config(
    page_title="日々のアクティビティ",
    page_icon=":material/directions_run:",
    layout="wide",
)

init_db()
st.title("日々のアクティビティ")
page = st.segmented_control(
    "表示する画面",
    ["記録", "振り返り"],
    default="記録",
    key="main_page",
)

if page == "記録":
    st.header("日々の記録")
    activity_date = st.date_input("記録日", value=date.today(), key="record_date")
    existing = get_daily_record(activity_date)
    date_key = activity_date.isoformat()

    st.subheader("日次データ")
    with st.form(f"daily_record_{date_key}"):
        sleep_col, steps_col, floors_col = st.columns(3)
        sleep_score = sleep_col.number_input(
            "睡眠スコア",
            min_value=0,
            max_value=100,
            value=existing.sleep_score if existing is not None else None,
            step=1,
            key=f"sleep_score_{date_key}",
        )
        steps = steps_col.number_input(
            "歩数",
            min_value=0,
            value=existing.steps if existing is not None else None,
            step=100,
            key=f"steps_{date_key}",
        )
        floors_climbed = floors_col.number_input(
            "登った階数",
            min_value=0,
            value=existing.floors_climbed if existing is not None else None,
            step=1,
            key=f"floors_{date_key}",
        )

        st.caption(
            "目標値は初期値です。実績と一緒に入力すると保存され、達成率を表示します。"
        )
        ring_cols = st.columns(3)
        move_kcal = ring_cols[0].number_input(
            "ムーブ実績 (kcal)",
            min_value=0.0,
            value=existing.move_kcal if existing is not None else None,
            step=1.0,
            key=f"move_kcal_{date_key}",
        )
        move_goal_kcal = ring_cols[0].number_input(
            "ムーブ目標 (kcal)",
            min_value=0.0,
            value=(
                existing.move_goal_kcal
                if existing is not None and existing.move_goal_kcal is not None
                else DEFAULT_MOVE_GOAL_KCAL
            ),
            step=1.0,
            key=f"move_goal_{date_key}",
        )
        exercise_minutes = ring_cols[1].number_input(
            "エクササイズ実績 (分)",
            min_value=0.0,
            value=existing.exercise_minutes if existing is not None else None,
            step=1.0,
            key=f"exercise_minutes_{date_key}",
        )
        exercise_goal_minutes = ring_cols[1].number_input(
            "エクササイズ目標 (分)",
            min_value=0.0,
            value=(
                existing.exercise_goal_minutes
                if existing is not None
                and existing.exercise_goal_minutes is not None
                else DEFAULT_EXERCISE_GOAL_MINUTES
            ),
            step=1.0,
            key=f"exercise_goal_{date_key}",
        )
        stand_hours = ring_cols[2].number_input(
            "スタンド実績 (時間)",
            min_value=0.0,
            value=existing.stand_hours if existing is not None else None,
            step=1.0,
            key=f"stand_hours_{date_key}",
        )
        stand_goal_hours = ring_cols[2].number_input(
            "スタンド目標 (時間)",
            min_value=0.0,
            value=(
                existing.stand_goal_hours
                if existing is not None and existing.stand_goal_hours is not None
                else DEFAULT_STAND_GOAL_HOURS
            ),
            step=1.0,
            key=f"stand_goal_{date_key}",
        )

        strength_minutes = st.number_input(
            "筋トレ時間 (分)",
            min_value=0.0,
            value=existing.strength_minutes if existing is not None else None,
            step=1.0,
            key=f"strength_minutes_{date_key}",
        )
        note = st.text_area(
            "メモ",
            value=existing.note if existing is not None else "",
            key=f"note_{date_key}",
        )
        daily_submitted = st.form_submit_button("日次データを保存")

    if daily_submitted:
        record = DailyRecord(
            activity_date=activity_date,
            sleep_score=sleep_score,
            steps=steps,
            floors_climbed=floors_climbed,
            move_kcal=move_kcal,
            move_goal_kcal=_ring_goal_for_save(
                move_kcal,
                move_goal_kcal,
                DEFAULT_MOVE_GOAL_KCAL,
                existing.move_goal_kcal if existing is not None else None,
            ),
            exercise_minutes=exercise_minutes,
            exercise_goal_minutes=_ring_goal_for_save(
                exercise_minutes,
                exercise_goal_minutes,
                DEFAULT_EXERCISE_GOAL_MINUTES,
                existing.exercise_goal_minutes if existing is not None else None,
            ),
            stand_hours=stand_hours,
            stand_goal_hours=_ring_goal_for_save(
                stand_hours,
                stand_goal_hours,
                DEFAULT_STAND_GOAL_HOURS,
                existing.stand_goal_hours if existing is not None else None,
            ),
            strength_minutes=strength_minutes,
            note=note,
        )
        try:
            save_daily_record(record)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("日次データを保存しました。")
            st.rerun()

    st.subheader("ランニング")
    with st.form(f"run_form_{date_key}"):
        run_distance = st.number_input(
            "距離 (km)",
            min_value=0.0,
            value=None,
            step=0.1,
            format="%.2f",
            key=f"run_distance_{date_key}",
        )
        run_duration = st.number_input(
            "時間 (分)",
            min_value=0.0,
            value=None,
            step=1.0,
            format="%.1f",
            key=f"run_duration_{date_key}",
        )
        run_submitted = st.form_submit_button("ランニングを追加")

    if run_submitted:
        if run_distance is None or run_distance <= 0:
            st.error("ランニング距離は0より大きく入力してください。")
        elif run_duration is None or run_duration <= 0:
            st.error("ランニング時間は0より大きく入力してください。")
        else:
            add_run(activity_date, float(run_distance), float(run_duration))
            st.success("ランニングを追加しました。")
            st.rerun()

    runs = list_runs(activity_date)
    if runs:
        run_rows = [
            {
                "距離 (km)": run.distance_km,
                "時間": format_duration(run.duration_seconds / 60),
                "ペース": format_pace(
                    run.duration_seconds, run.distance_km
                ),
            }
            for run in runs
        ]
        st.dataframe(
            pd.DataFrame(run_rows),
            hide_index=True,
            alt="選択した日のランニング記録",
        )
        for run in runs:
            if st.button(
                f"ランニングを削除: {run.distance_km:g} km",
                key=f"delete_run_{run.id}",
                icon=":material/delete:",
            ):
                delete_run(run.id)
                st.rerun()
    else:
        st.caption("この日のランニング記録はありません。")

    st.subheader("筋トレ")
    st.caption("種目は自由入力または候補から選択できます。1セットにつき一方を入力してください。")
    empty_sets = pd.DataFrame(
        {
            "種目 (自由入力)": pd.Series(dtype="string"),
            "種目 (候補選択)": pd.Series(dtype="string"),
            "重量 (kg)": pd.Series(dtype="float64"),
            "回数": pd.Series(dtype="int64"),
        }
    )
    with st.form(f"strength_form_{date_key}"):
        edited_sets = st.data_editor(
            empty_sets,
            num_rows="dynamic",
            column_config={
                "種目 (自由入力)": st.column_config.TextColumn(
                    "種目 (自由入力)"
                ),
                "種目 (候補選択)": st.column_config.SelectboxColumn(
                    "種目 (候補選択)", options=TRAINING_EXERCISES
                ),
                "重量 (kg)": st.column_config.NumberColumn(
                    "重量 (kg)", min_value=0.0, step=0.5, format="%.1f"
                ),
                "回数": st.column_config.NumberColumn(
                    "回数", min_value=1, step=1, format="%d"
                ),
            },
            hide_index=True,
            key=f"strength_editor_{date_key}",
            alt="追加する筋トレのセット",
        )
        strength_submitted = st.form_submit_button("筋トレセットを追加")

    if strength_submitted:
        try:
            rows = []
            for row in edited_sets.to_dict(orient="records"):
                free_exercise = (
                    None
                    if pd.isna(row["種目 (自由入力)"])
                    else str(row["種目 (自由入力)"]).strip() or None
                )
                selected_exercise = (
                    None
                    if pd.isna(row["種目 (候補選択)"])
                    else str(row["種目 (候補選択)"]).strip() or None
                )
                if free_exercise is not None and selected_exercise is not None:
                    raise ValueError(
                        "筋トレの種目は自由入力か候補選択のどちらか一方にしてください。"
                    )
                rows.append(
                    {
                        "exercise": free_exercise or selected_exercise,
                        "weight_kg": (
                            float(row["重量 (kg)"])
                            if not pd.isna(row["重量 (kg)"])
                            else None
                        ),
                        "repetitions": (
                            int(row["回数"])
                            if not pd.isna(row["回数"])
                            else None
                        ),
                    }
                )
            inserted = add_strength_sets(activity_date, rows)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success(f"{inserted}セットを追加しました。")
            st.rerun()

    strength_sets = list_strength_sets(activity_date)
    if strength_sets:
        set_rows = [
            {
                "種目": item.exercise,
                "重量 (kg)": item.weight_kg,
                "回数": item.repetitions,
            }
            for item in strength_sets
        ]
        st.dataframe(
            pd.DataFrame(set_rows),
            hide_index=True,
            alt="選択した日の筋トレ記録",
        )
        for item in strength_sets:
            if st.button(
                f"セットを削除: {item.exercise} {item.weight_kg} kg × {item.repetitions}回",
                key=f"delete_strength_set_{item.id}",
                icon=":material/delete:",
            ):
                delete_strength_set(item.id)
                st.rerun()
    else:
        st.caption("この日の筋トレセットはありません。")

    saved_record = get_daily_record(activity_date)
    if saved_record is not None:
        st.subheader("リング達成率")
        progress_columns = st.columns(3)
        for column, label, actual, goal in (
            (
                progress_columns[0],
                "ムーブ",
                saved_record.move_kcal,
                saved_record.move_goal_kcal,
            ),
            (
                progress_columns[1],
                "エクササイズ",
                saved_record.exercise_minutes,
                saved_record.exercise_goal_minutes,
            ),
            (
                progress_columns[2],
                "スタンド",
                saved_record.stand_hours,
                saved_record.stand_goal_hours,
            ),
        ):
            if actual is not None and goal is not None:
                ratio = actual / goal
                column.progress(min(ratio, 1.0), text=f"{label}: {ratio:.0%}")

else:
    st.header("振り返り")
    period = st.segmented_control(
        "集計単位",
        ["日", "週", "月"],
        default="日",
        key="summary_period",
    )
    selected_range = st.date_input(
        "期間",
        value=(date.today() - timedelta(days=89), date.today()),
        key="history_range",
    )
    if (
        not isinstance(selected_range, tuple)
        or len(selected_range) != 2
        or any(day is None for day in selected_range)
    ):
        st.info("開始日と終了日を選択してください。")
    else:
        start_date, end_date = selected_range
        if start_date > end_date:
            st.error("期間の開始日は終了日より前にしてください。")
        else:
            records = get_history(start_date, end_date)
            if not records:
                st.info("選択した期間の記録はありません。")
            else:
                if period is None:
                    st.info("集計単位を選択してください。")
                    st.stop()
                history = summarize_history(records, period)
                run_minutes = sum(record.run_duration_minutes for record in records)
                strength_minutes_values = [
                    record.strength_minutes
                    for record in records
                    if record.strength_minutes is not None
                ]
                strength_minutes_total = sum(strength_minutes_values)
                total_distance = sum(record.run_distance_km for record in records)
                with st.container(horizontal=True):
                    st.metric(
                        "ランニング時間合計",
                        format_duration(run_minutes),
                        border=True,
                    )
                    st.metric(
                        "筋トレ時間合計",
                        format_duration(strength_minutes_total),
                        border=True,
                    )
                    st.metric(
                        "ランニング距離合計",
                        f"{total_distance:.2f} km",
                        border=True,
                    )

                metrics = {
                    "睡眠スコア": ("sleep_score", "点"),
                    "歩数": ("steps", "歩"),
                    "登った階数": ("floors_climbed", "階"),
                    "ランニング距離": ("run_distance_km", "km"),
                    "ランニング時間": ("run_duration_minutes", "分"),
                    "ランニングペース": ("run_pace_minutes_per_km", "分/km"),
                    "筋トレ時間": ("strength_minutes", "分"),
                    "筋トレ総負荷": ("strength_volume_kg_reps", "kg × 回"),
                    "ムーブ達成率": ("move_progress_pct", "%"),
                    "エクササイズ達成率": ("exercise_progress_pct", "%"),
                    "スタンド達成率": ("stand_progress_pct", "%"),
                }
                metric_label = st.selectbox("グラフにする項目", list(metrics))
                metric_column, unit = metrics[metric_label]
                chart_data = history[["activity_date", metric_column]].rename(
                    columns={metric_column: "値"}
                )
                chart_data = chart_data.dropna(subset=["値"])
                if chart_data.empty:
                    st.info(f"{metric_label}の記録はありません。")
                else:
                    st.line_chart(
                        chart_data,
                        x="activity_date",
                        y="値",
                        y_label=unit,
                        alt=f"{period}ごとの{metric_label}の推移",
                    )

                table_columns = {
                    "activity_date": "日付",
                    "sleep_score": "睡眠スコア",
                    "steps": "歩数",
                    "floors_climbed": "登った階数",
                    "run_distance_km": "ランニング距離 (km)",
                    "run_duration_minutes": "ランニング時間 (分)",
                    "strength_minutes": "筋トレ時間 (分)",
                    "strength_set_count": "筋トレセット数",
                    "move_progress_pct": "ムーブ達成率 (%)",
                    "exercise_progress_pct": "エクササイズ達成率 (%)",
                    "stand_progress_pct": "スタンド達成率 (%)",
                }
                table = history[list(table_columns)].rename(columns=table_columns)
                st.dataframe(
                    table,
                    hide_index=True,
                    alt=f"{period}ごとのアクティビティ記録",
                )
