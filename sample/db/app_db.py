import os
import sqlite3
from datetime import datetime
import streamlit as st
from google import genai

# ページ設定
st.title("文章タイトル生成 & 保存")

# データベースパス
db_path = os.path.join(os.path.dirname(__file__), "articles.db")

# データベース初期化
def init_db():
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
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

# 文章入力
content = st.text_area("文章を入力してください", height=200)

if st.button("保存"):
    if content:
        # Geminiでタイトル生成
        response = client.models.generate_content(
            model=model,
            contents=f"以下の文章に適切な短いタイトルをつけてください。タイトルのみを出力してください。\n\n{content}"
        )
        title = response.text.strip()
        
        # DBに保存
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO articles (title, content, created_at) VALUES (?, ?, ?)",
            (title, content, datetime.now())
        )
        conn.commit()
        conn.close()
        
        st.success(f"保存しました！ タイトル: {title}")
    else:
        st.warning("文章を入力してください")

# 保存済み記事一覧
st.subheader("保存済み記事")
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT title, content, created_at FROM articles ORDER BY created_at DESC").fetchall()
conn.close()

for title, text, created_at in rows:
    with st.expander(f"📄 {title} ({created_at})"):
        st.write(text)
