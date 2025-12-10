# 必要なライブラリのインポート
import os  # 環境変数にアクセスするために使用
import sqlite3  # SQLiteデータベース操作のために使用
from datetime import datetime  # タイムスタンプのために使用
import time  # スリープ用
import streamlit as st  # Streamlit UIフレームワーク
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
# このスクリプトと同じディレクトリにgame_suggestions.dbを作成
db_path = os.path.join(os.path.dirname(__file__), "game_suggestions.db")


def safe_rerun():
    """Streamlit の再実行を安全に行う（存在すれば呼び出す）。

    `st.experimental_rerun` が存在しない環境でも AttributeError を出さないようにする。
    最終手段としてセッションステートのトリガーをトグルして間接的に再描画を促す。
    """
    rerun_func = getattr(st, "experimental_rerun", None)
    if callable(rerun_func):
        try:
            rerun_func()
            return
        except Exception:
            pass

    # フォールバック: セッションステートの値を反転して UI を更新させる
    st.session_state["_rerun_trigger"] = not st.session_state.get("_rerun_trigger", False)


def init_database():
    """
    データベースとテーブルを初期化する関数
    テーブルが存在しない場合のみ作成する
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ゲーム提案を保存するテーブルを作成
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mood TEXT NOT NULL,
            opinion TEXT NOT NULL,
            suggested_game TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()


def save_game_suggestion(mood: str, opinion: str, suggested_game: str) -> int:
    """
    ゲーム提案をタイムスタンプとともにデータベースに保存する関数
    
    Args:
        mood: ユーザーの気分
        opinion: ゲームに関する意見
        suggested_game: 提案されたゲームタイトル
    
    Returns:
        保存されたレコードのID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 現在のタイムスタンプを取得
    timestamp = datetime.now()
    
    # ゲーム提案とタイムスタンプをデータベースに挿入
    cursor.execute(
        "INSERT INTO game_suggestions (mood, opinion, suggested_game, created_at) VALUES (?, ?, ?, ?)",
        (mood, opinion, suggested_game, timestamp)
    )
    
    # 挿入されたレコードのIDを取得
    record_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return record_id


def get_all_suggestions():
    """
    保存されているすべてのゲーム提案を取得する関数
    
    Returns:
        ゲーム提案のリスト（id, mood, opinion, suggested_game, created_at）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, mood, opinion, suggested_game, created_at FROM game_suggestions ORDER BY created_at DESC")
    suggestions = cursor.fetchall()
    
    conn.close()
    
    return suggestions


def generate_game_suggestion(mood: str, opinion: str) -> str:
    """
    Gemini APIを使用してゲーム提案を生成する関数
    
    Args:
        mood: ユーザーの気分
        opinion: ゲームに関する意見
    
    Returns:
        提案されたゲームタイトル（複数、改行で区切られた形式）
    """
    # プロンプト（ユーザーからの入力）の構築
    # Contentオブジェクトのリストとして会話履歴を表現する
    contents = [
        types.Content(
            role="user",  # メッセージの送信者（ユーザー）を指定
            parts=[
                # Part.from_text()でテキスト形式のメッセージを作成
                types.Part.from_text(text=f"""以下の気分と意見に基づいて、実際に存在する人気のゲームタイトルを5つ提案してください。必ず実在するゲームのみを提案し、架空のゲームは絶対に含めないでください。各タイトルは改行で区切って、ゲームタイトルのみを出力してください。

気分: {mood}
意見: {opinion}"""),
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

# ページ設定
st.title("🎮 ゲーム提案 AI")

# 気分と意見を入力
st.subheader("あなたの気分や意見を教えてください")
mood = st.text_input("現在の気分は？ (例: 疲れている、興奮している、リラックスしたい)")
opinion = st.text_area("ゲームに関する意見やジャンルの好み (例: アクション好き、ストーリー重視、短時間プレイ)", height=100)

if st.button("ゲームを提案してもらう"):
    if mood and opinion:
        # ゲーム提案を生成
        with st.spinner("提案を生成中..."):
            suggested_games_text = generate_game_suggestion(mood, opinion)
            suggested_games = suggested_games_text.strip().split('\n')
            # 空行を削除
            suggested_games = [game.strip() for game in suggested_games if game.strip()]
        
        # DBに保存（複数のゲーム）
        conn = sqlite3.connect(db_path)
        for game in suggested_games:
            conn.execute(
                "INSERT INTO game_suggestions (mood, opinion, suggested_game, created_at) VALUES (?, ?, ?, ?)",
                (mood, opinion, game, datetime.now())
            )
        conn.commit()
        conn.close()
        
        st.success("✨ おすすめゲーム（複数）:")
        for i, game in enumerate(suggested_games, 1):
            steam_url = f"https://store.steampowered.com/search/?term={game.replace(' ', '+')}"
            official_url = f"https://www.google.com/search?q={game.replace(' ', '+')}+official+website"
            youtube_url = f"https://www.youtube.com/results?search_query={game.replace(' ', '+')}+official+trailer"
            
            st.write(f"{i}. **{game}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"[🔗 Steamで検索]({steam_url})")
            with col2:
                st.write(f"[🌐 公式サイト]({official_url})")
            with col3:
                st.write(f"[▶️ YouTubeで検索]({youtube_url})")
            
            st.divider()
    else:
        st.warning("気分と意見の両方を入力してください")

# 提案履歴一覧
st.subheader("📋 提案履歴")

if 'confirm_delete_all' not in st.session_state:
    st.session_state['confirm_delete_all'] = False

conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT id, mood, opinion, suggested_game, created_at FROM game_suggestions ORDER BY created_at DESC").fetchall()
conn.close()

col_l, col_r = st.columns([3, 1])
with col_r:
    if st.button("🗑️ すべて削除", key="delete_all_btn"):
        st.session_state['confirm_delete_all'] = True

if st.session_state['confirm_delete_all']:
    st.warning("本当にすべての提案履歴を削除しますか？この操作は取り消せません。")
    if st.button("削除を確定する", key="confirm_delete_all_confirm"):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM game_suggestions")
        conn.commit()
        conn.close()
        st.session_state['confirm_delete_all'] = False
        safe_rerun()

if rows:
    for row in rows:
        row_id, mood_hist, opinion_hist, game, created_at = row
        with st.expander(f"🎯 {game} ({created_at})"):
            st.write(f"**気分:** {mood_hist}")
            st.write(f"**意見:** {opinion_hist}")

            col_del, col_spacer = st.columns([1, 4])
            with col_del:
                confirm_key = f"confirm_delete_{row_id}"
                if not st.session_state.get(confirm_key, False):
                    if st.button("削除", key=f"delete_{row_id}"):
                        st.session_state[confirm_key] = True
                else:
                    st.warning("本当にこの提案を削除しますか？この操作は取り消せません。")
                    if st.button("削除を確定する", key=f"confirm_{row_id}"):
                        conn = sqlite3.connect(db_path)
                        conn.execute("DELETE FROM game_suggestions WHERE id = ?", (row_id,))
                        conn.commit()
                        conn.close()
                        st.session_state[confirm_key] = False
                        safe_rerun()
                    if st.button("キャンセル", key=f"cancel_{row_id}"):
                        st.session_state[confirm_key] = False
else:
    st.info("まだ提案履歴がありません")