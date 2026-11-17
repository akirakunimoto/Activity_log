# テスト方法

## 1. 前提条件

ワークスペースのルートでPowerShellを起動し、Python仮想環境が `.venv` にあることを確認する。初回は依存関係をインストールする。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 2. 自動テスト

### 2.1 単体テスト実行

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

一時ディレクトリにSQLite DBを作成して実行する。テスト後に一時DBは破棄され、ユーザーの実データにはアクセスしない。

### 2.2 テスト対象

| テスト | 主な確認内容 |
| --- | --- |
| `test_daily_record_upsert_and_ring_validation` | 同日保存で日次データが更新されること、リング実績・目標の片側入力が拒否されること |
| `test_runs_and_strength_sets_are_saved_and_deletable` | 複数ランニングと複数セットの保存・一覧・削除、距離・時間・筋トレ総負荷の集約 |
| `test_history_rejects_reversed_date_range` | 開始日が終了日より後の履歴検索を拒否すること |
| `test_pace_and_duration_formatting` | ペース計算、0距離の扱い、時間・ペース表示形式 |
| `test_weekly_summary_uses_totals_and_ring_completion_ratio` | 週の合計・睡眠平均・ランニングペース・リング合計達成率 |

テストは `tests/test_storage.py` と `tests/test_analytics.py` にある。

### 2.3 型チェック

```powershell
.\.venv\Scripts\ty.exe check streamlit_app.py activity_log tests
```

`All checks passed!` が表示され、診断がないことを確認する。

## 3. UIの手動確認

アプリを起動する。

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

ローカルブラウザーで次を確認する。

1. **日次データ**: 睡眠、歩数、階数、筋トレ時間、メモを入力して保存する。同じ日を再選択し、値が再表示されることを確認する。
2. **リング**: 未設定の目標値がムーブ550 kcal、エクササイズ30分、スタンド12時間で表示されることを確認する。実績を入力せず他の日次データを保存でき、初期目標値は保存されないことを確認する。実績を入力すると初期目標値と一緒に保存されて達成率が表示されること、目標値を消して実績だけ、または初期値以外の目標だけで送信するとエラーとなることを確認する。
3. **ランニング**: 例として5 km・25分と3 km・18分を同日に登録する。2行が表示され、それぞれ `5:00 min/km` と `6:00 min/km` になること、各行を個別削除できることを確認する。
4. **筋トレ**: 候補から選択した種目と自由入力した種目を含む複数セットを登録する。全セットが別々に表示され、個別削除できることを確認する。
5. **振り返り**: 期間を記録日に合わせ、日・週・月を切り替える。睡眠、歩数、ランニング距離、ペース、筋トレ、リング達成率の各項目を選び、グラフ・一覧の集計を確認する。
6. **時間合計**: ランニング時間と筋トレ時間が別々のカードに表示され、片方にもう片方が加算されていないことを確認する。
7. **空状態**: 記録のない日付範囲、または値のないグラフ項目でエラーにならず説明が表示されることを確認する。

## 4. Streamlit実アプリのヘッドレス確認（任意）

Agent APIを有効にして起動する方法。ポートを利用可能な値に変更してもよい。

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless=true --server.address=127.0.0.1 --server.port=8765 --server.enableAgentApi=true
```

別のPowerShellでヘルスチェックと初期画面を確認する。

```powershell
Invoke-RestMethod http://127.0.0.1:8765/_stcore/health
Invoke-RestMethod -Uri http://127.0.0.1:8765/_stcore/agent/interact -Method Post -ContentType 'application/json' -Body '{}'
```

Agent APIの応答が `status=ready` であり、`actions` に記録日・日次入力・各画面切替等のウィジェットが含まれることを確認する。振り返り画面への切替は、同じセッションIDを使って次のように行う。

```powershell
$sessionId = '<初期応答のsession_id>'
$body = '{"session_id":"' + $sessionId + '","widget_state":{"main_page":"\u632f\u308a\u8fd4\u308a"}}'
Invoke-RestMethod -Uri http://127.0.0.1:8765/_stcore/agent/interact -Method Post -ContentType 'application/json' -Body $body
```

記録の追加・削除はDBに書き込む操作である。アプリはワークスペース直下の `activity.sqlite3` を使うため、本番データを避けて画面を確認する場合は、ワークスペースを一時ディレクトリへコピーしてそのコピーから起動する。確認後はサーバーを停止し、一時コピーを破棄する。

## 5. 合格基準

- 自動テストがすべて成功する。
- 型チェックにエラーがない。
- 記録画面と振り返り画面を表示して切り替えられる。
- 手動確認の入力・保存・再表示・削除・集計が要求事項に合致する。
- アプリのコンソールに新たな例外や未解消の警告がない。
