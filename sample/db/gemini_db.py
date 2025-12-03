# 必要なライブラリのインポート
import os  # 環境変数にアクセスするために使用
import sqlite3  # SQLiteデータベース操作のために使用
from datetime import datetime  # タイムスタンプのために使用
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

# データベースファイルのパス
# このスクリプトと同じディレクトリにhaiku.dbを作成
db_path = os.path.join(os.path.dirname(__file__), "haiku.db")


def init_database():
    """
    データベースとテーブルを初期化する関数
    テーブルが存在しない場合のみ作成する
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 俳句を保存するテーブルを作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS haikus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haiku TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def save_haiku(haiku: str) -> int:
    """
    俳句をタイムスタンプとともにデータベースに保存する関数
    
    Args:
        haiku: 保存する俳句のテキスト
    
    Returns:
        保存されたレコードのID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 現在のタイムスタンプを取得
    timestamp = datetime.now()
    
    # 俳句とタイムスタンプをデータベースに挿入
    cursor.execute(
        "INSERT INTO haikus (haiku, created_at) VALUES (?, ?)",
        (haiku, timestamp)
    )
    
    # 挿入されたレコードのIDを取得
    record_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return record_id


def get_all_haikus():
    """
    保存されているすべての俳句を取得する関数
    
    Returns:
        俳句のリスト（id, haiku, created_at）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, haiku, created_at FROM haikus ORDER BY created_at DESC")
    haikus = cursor.fetchall()
    
    conn.close()
    
    return haikus


def generate_haiku() -> str:
    """
    Gemini APIを使用して俳句を生成する関数
    
    Returns:
        生成された俳句のテキスト
    """
    # プロンプト（ユーザーからの入力）の構築
    # Contentオブジェクトのリストとして会話履歴を表現する
    contents = [
        types.Content(
            role="user",  # メッセージの送信者（ユーザー）を指定
            parts=[
                # Part.from_text()でテキスト形式のメッセージを作成
                types.Part.from_text(text="俳句を作ってください。俳句のみを出力してください。"),
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
    
    return response.text


# データベースを初期化
init_database()

# 俳句を生成
print("--- 俳句を生成中 ---")
haiku = generate_haiku()
print(f"生成された俳句:\n{haiku}")

# 俳句をデータベースに保存
record_id = save_haiku(haiku)
print(f"\n--- データベースに保存しました (ID: {record_id}) ---")

# 保存されているすべての俳句を表示
print("\n--- 保存されている俳句一覧 ---")
all_haikus = get_all_haikus()
for haiku_record in all_haikus:
    id_, haiku_text, created_at = haiku_record
    print(f"[ID: {id_}] {created_at}")
    print(f"{haiku_text}")
    print("-" * 30)