# ✏️ LLM Prompt Editor

AWS Bedrock (Claude Sonnet 4.6) を使ってプロンプトを自動採点・改善するツールです。

## 機能

- プロンプトを6観点（明確さ・具体性・役割設定・出力形式・コンテキスト・制約条件）で自動採点
- 改善されたプロンプトを自動生成
- 採点履歴の保存・復元（最大20件）
- 改善案を反映して繰り返し再採点
- 実際のAI回答のテスト実行

## 前提条件

- Windows 10/11 + WSL2 (Ubuntu)
- SOLIZEのAWS SSOアカウント（PowerUser-980268627924）
- Python 3.10以上（WSL内）

---

## 初回セットアップ（初回のみ）

### 1. リポジトリのクローン

```bash
git clone https://github.com/KENFUJIEDA-cloud/prompt-editor.git ~/pe_bedrock
cd ~/pe_bedrock
```

### 2. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 3. .venv自動有効化の設定（任意）

毎回手動でvenvを有効化しなくて済むよう設定します。

```bash
echo 'source ~/udast-docker/UDASTV2/.venv/bin/activate' >> ~/.bashrc
source ~/.bashrc
```

> すでにUDASTVの.venvを使用している場合はスキップしてください。

---

## 毎回の起動手順

### 1. AWS SSOログイン

```bash
aws sso login --profile PowerUser-980268627924
```

ブラウザが開くのでSOLIZEのSSOアカウントでログインして認証を完了してください。

> セッションは約8時間で期限切れになります。エラーが出た場合は再度実行してください。

### 2. アプリの起動

```bash
cd ~/pe_bedrock
source <(aws configure export-credentials --profile PowerUser-980268627924 --format env | grep -v EXPIRATION)
streamlit run app.py --server.port 8502
```

### 3. ブラウザでアクセス

```
http://localhost:8502
```

---

## 使い方

### プロンプトの採点

1. 左側の入力欄にプロンプトを入力する
2. 「🔍 採点して改善案を生成」ボタンを押す
3. 右側に6観点のスコアと指摘事項が表示される
4. 画面下部に改善されたプロンプトが表示される

### 改善案の活用

- 「⬆️ 改善案を入力欄に反映して再採点」で改善案をそのまま再採点できる
- 「📥 ダウンロード」で改善案をテキストファイルとして保存できる

### AIの回答テスト

採点後に「▶️ このプロンプトでAIに問い合わせる」ボタンで実際のAI回答を確認できる。

---

## トラブルシューティング

| エラー | 対処法 |
|--------|--------|
| `Token has expired` | `aws sso login --profile PowerUser-980268627924` を再実行する |
| `streamlit: command not found` | `source ~/.bashrc` を実行してvenvを有効化する |
| 採点中のまま止まる | Ctrl+Cでアプリを止め、手順2からやり直す |
| `AccessDenied` | SSOセッションが切れている。手順1からやり直す |

---