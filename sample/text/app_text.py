import os
import streamlit as st
from google import genai
from google.genai import types

# ページ設定
st.title("Gemini Chat")

# Gemini APIクライアントの初期化
@st.cache_resource
def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

client = get_client()
model = "gemini-flash-lite-latest"

# セッションステートで会話履歴を管理
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去のメッセージを表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力を受け取る
if prompt := st.chat_input("メッセージを入力してください"):
    # ユーザーメッセージを表示して履歴に追加
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 会話履歴をGemini形式に変換
    contents = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg["content"])])
        )

    # Gemini APIにリクエストを送信
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig()
    )

    # アシスタントの応答を表示して履歴に追加
    with st.chat_message("assistant"):
        st.markdown(response.text)
    st.session_state.messages.append({"role": "assistant", "content": response.text})
