import os
import sqlite3
from datetime import datetime
import time
import streamlit as st
from google import genai

# ページ設定
st.title("🎮 ゲーム提案 AI")

# データベースパス
db_path = os.path.join(os.path.dirname(__file__), "game_history.db")

# データベース初期化
def init_db():
    conn = sqlite3.connect(db_path)
    conn.execute("""
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

init_db()

# Gemini APIクライアントの初期化
@st.cache_resource
def get_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

client = get_client()
model = "gemini-flash-lite-latest"


def generate_one_line_descriptions(titles):
    """Given a list of titles, ask the model to return one-line descriptions in the same order.
    Returns a list of descriptions (same length as titles, padded with '説明なし' if missing).
    """
    if not titles:
        return []

    prompt = (
        "以下のゲームタイトルについて、それぞれ1行で簡潔に説明してください。"
        " タイトルは出力せず、タイトルの順に対応する説明だけを改行区切りで出力してください。\n\n"
        + "\n".join(titles)
    )

    try:
        resp = client.models.generate_content(model=model, contents=prompt)
        lines = [l.strip() for l in resp.text.strip().split('\n') if l.strip()]
    except Exception:
        lines = []

    # 必要なら不足分を埋める
    if len(lines) < len(titles):
        lines += ["説明なし"] * (len(titles) - len(lines))

    return lines


# 気分と意見を入力
st.subheader("あなたの気分や意見を教えてください")
mood = st.text_input("現在の気分は？ (例: 疲れている、興奮している、リラックスしたい)")
opinion = st.text_area("ゲームに関する意見やジャンルの好み (例: アクション好き、ストーリー重視、短時間プレイ)", height=100)

if st.button("ゲームを提案してもらう"):
    if mood or opinion:
        # 入力に応じてプロンプトのユーザー情報部分を組み立てる
        user_state_section = "【ユーザーの状態】\n"
        if mood:
            user_state_section += f"気分: {mood}\n\n"
        else:
            user_state_section += "気分: 情報なし\n\n"

        prefs_section = "【ゲームの好み・要望】\n"
        if opinion:
            prefs_section += f"{opinion}\n\n"
        else:
            prefs_section += "なし\n\n"

        # Geminiでゲーム提案（複数取得）
        response = client.models.generate_content(
            model=model,
            contents=f"""以下のユーザーの気分と意見を詳しく分析して、最も適切なゲームタイトルを10個提案してください。

{user_state_section}{prefs_section}

【提案の条件】
1. 必ず実在する有名なゲームのみを提案してください
2. 架空のゲームは絶対に含めないでください
3. ユーザーの気分と意見を最大限に考慮してください
4. 各タイトルは改行で区切ってください
5. ゲームタイトルのみを出力してください（説明は不要）"""
        )
        suggested_games = response.text.strip().split('\n')
        # 空行を削除
        suggested_games = [game.strip() for game in suggested_games if game.strip()]

        # 各ゲームの一言説明を生成
        try:
            descriptions = generate_one_line_descriptions(suggested_games)
        except Exception:
            descriptions = ["説明なし"] * len(suggested_games)

        # DBに保存（複数のゲーム）
        conn = sqlite3.connect(db_path)
        for game in suggested_games:
            conn.execute(
                "INSERT INTO game_suggestions (mood, opinion, suggested_game, created_at) VALUES (?, ?, ?, ?)",
                (mood or "", opinion or "", game, datetime.now())
            )
        conn.commit()
        conn.close()

        st.success("✨ おすすめゲーム（10件）:")
        for i, game in enumerate(suggested_games, 1):
            steam_url = f"https://store.steampowered.com/search/?term={game.replace(' ', '+')}"
            official_url = f"https://www.google.com/search?q={game.replace(' ', '+')}+official+website"
            youtube_url = f"https://www.youtube.com/results?search_query={game.replace(' ', '+')}+official+trailer"

            st.write(f"{i}. **{game}**")
            # 一言説明を表示（存在すれば）
            if i-1 < len(descriptions):
                st.write(f"*{descriptions[i-1]}*")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"[🔗 Steamで検索]({steam_url})")
            with col2:
                st.write(f"[🌐 公式サイト]({official_url})")
            with col3:
                st.write(f"[▶️ YouTubeで検索]({youtube_url})")

            st.divider()
    else:
        st.warning("気分または意見のいずれかを入力してください")

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
        rerun_func = getattr(st, "experimental_rerun", None)
        if callable(rerun_func):
            try:
                rerun_func()
            except Exception:
                if hasattr(st, "rerun"):
                    st.rerun()

if rows:
    for row in rows:
        row_id, mood, opinion, game, created_at = row
        with st.expander(f"🎯 {game} ({created_at})"):
            st.write(f"**気分:** {mood}")
            st.write(f"**意見:** {opinion}")

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
                        rerun_func = getattr(st, "experimental_rerun", None)
                        if callable(rerun_func):
                            try:
                                rerun_func()
                            except Exception:
                                if hasattr(st, "rerun"):
                                    st.rerun()
                    if st.button("キャンセル", key=f"cancel_{row_id}"):
                        st.session_state[confirm_key] = False
else:
    st.info("まだ提案履歴がありません")
