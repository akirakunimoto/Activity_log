# 日々のアクティビティ記録

Streamlit と SQLite を使った、個人用のローカル記録ツールです。データはワークスペースのルートにある `activity.sqlite3` に保存され、外部サービスには送信しません。ワークスペースがOneDriveなどの同期対象フォルダー内にある場合、このDBも同期されます。DBファイルはGitの追跡対象外です。

## ドキュメント

- [ドキュメント一覧](doc/README.md)
- [要求事項](doc/requirements.md)
- [詳細設計](doc/design.md)
- [テスト方法](doc/testing.md)

## セットアップと起動

PowerShell でワークスペースのルートから実行します。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

ローカルのブラウザーで表示された URL を開きます。記録データをバックアップする場合は、アプリを終了してからワークスペース直下の `activity.sqlite3` をコピーしてください。

## テストと型チェック

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\ty.exe check streamlit_app.py activity_log tests
```
