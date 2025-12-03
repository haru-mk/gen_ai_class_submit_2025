import os
import sqlite3
from datetime import datetime
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

# 気分と意見を入力
st.subheader("あなたの気分や意見を教えてください")
mood = st.text_input("現在の気分は？ (例: 疲れている、興奮している、リラックスしたい)")
opinion = st.text_area("ゲームに関する意見やジャンルの好み (例: アクション好き、ストーリー重視、短時間プレイ)", height=100)

if st.button("ゲームを提案してもらう"):
    if mood and opinion:
        # Geminiでゲーム提案（複数取得）
        response = client.models.generate_content(
            model=model,
            contents=f"""以下のユーザーの気分と意見を詳しく分析して、最も適切なゲームタイトルを5つ提案してください。

【ユーザーの状態】
気分: {mood}

【ゲームの好み・要望】
{opinion}

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
            
            # ゲーム画像をiframeで表示
            image_html = f"""
            <iframe src="https://www.google.com/search?q={game.replace(' ', '+')}+game&tbm=isch" 
                    style="width:100%; height:400px; border:none; border-radius:8px;"></iframe>
            """
            st.markdown(image_html, unsafe_allow_html=True)
            
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
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT mood, opinion, suggested_game, created_at FROM game_suggestions ORDER BY created_at DESC").fetchall()
conn.close()

if rows:
    for mood, opinion, game, created_at in rows:
        with st.expander(f"🎯 {game} ({created_at})"):
            st.write(f"**気分:** {mood}")
            st.write(f"**意見:** {opinion}")
else:
    st.info("まだ提案履歴がありません")
