# 必要なライブラリのインポート
import os  # 環境変数にアクセスするために使用
import json  # JSONデータの操作に使用
from google import genai  # Google GenAI APIのメインモジュール
from google.genai import types  # APIリクエストとレスポンスの型定義

# 環境変数からGemini APIキーを取得
# セキュリティのため、APIキーはコードに直接記述せず環境変数から取得する
api_key = os.environ.get("GEMINI_API_KEY")

# Google GenAI クライアントの初期化
# このクライアントを通じてGemini APIとやり取りする
client = genai.Client(
    api_key=api_key,
)

# 使用するモデルの指定
# gemini-flash-lite-latestは高速で軽量なFlashモデルの最新版
model = "gemini-flash-lite-latest"

# サンプルテキスト
sample_text = "春の訪れとともに、桜の花が咲き始めました。風に舞う花びらが美しい季節です。"

# プロンプト（ユーザーからの入力）の構築
# Contentオブジェクトのリストとして会話履歴を表現する
contents = [
    types.Content(
        role="user",  # メッセージの送信者（ユーザー）を指定
        parts=[
            # Part.from_text()でテキスト形式のメッセージを作成
            types.Part.from_text(
                text=f"次のテキストについて俳句を作成してください:\n{sample_text}\n出力はJSON形式{{'haiku': 'ここに俳句','kigo': '春or夏or秋or冬or不明'}}です。他の情報は含めないでください。"
            ),
        ],
    ),
]

# コンテンツ生成の設定
# GenerateContentConfigで生成時の詳細なパラメータを指定できる
generate_content_config = types.GenerateContentConfig()

# Gemini APIを呼び出してコンテンツを生成
# generate_content()メソッドでモデルにプロンプトを送信し、レスポンスを受け取る
response = client.models.generate_content(
    model=model,  # 使用するモデル
    contents=contents,  # プロンプト内容
    config=generate_content_config,  # 生成設定
)

# 生成結果の表示
print("--- 生成結果 (JSON形式) ---")
# response.textで生成されたテキストを取得
print(response.text)
print("------\n")

# 生成結果をJSONとして解析
try:
    # レスポンステキストを取得
    response_text = response.text.strip()

    # マークダウン形式のコードブロックを除去
    # ```json ... ``` や ``` ... ``` の形式に対応
    if response_text.startswith("```"):
        # 最初の```とその行を除去
        lines = response_text.split("\n")
        # 最初の行が```jsonまたは```の場合は除去
        if lines[0].startswith("```"):
            lines = lines[1:]
        # 最後の行が```の場合は除去
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    # JSONとしてパース
    haiku_data = json.loads(response_text)

    # 俳句と季語の表示
    if "haiku" in haiku_data and "kigo" in haiku_data:
        print("--- パース成功 ---")
        print(f"俳句: {haiku_data['haiku']}")
        print(f"季語: {haiku_data['kigo']}")
        print("------\n")
    else:
        print("--- エラー: 'haiku'キーが見つかりません ---")
        print(f"取得したデータ: {haiku_data}")
        print("------\n")

except json.JSONDecodeError as e:
    print("--- JSONパースエラー ---")
    print(f"エラー: {e}")
    print(f"受信したテキスト:\n{response.text}")
    print("------\n")
