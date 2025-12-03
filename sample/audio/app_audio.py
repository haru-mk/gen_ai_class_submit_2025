import os
import streamlit as st
from google import genai
from google.genai import types

# ページ設定
st.title("音声説明アプリ")
st.write("音声ファイルをアップロードすると、AIが説明してくれます")

# サンプル音声のダウンロードボタン
if os.path.exists("sample.mp3"):
    with open("sample.mp3", "rb") as f:
        sample_audio_bytes = f.read()
    st.download_button(
        label="サンプル音声をダウンロード",
        data=sample_audio_bytes,
        file_name="sample.mp3",
        mime="audio/mp3",
    )

# 音声アップロード
uploaded_file = st.file_uploader("音声ファイルを選択してください", type=["mp3", "wav", "m4a"])

if uploaded_file is not None:
    # アップロードされた音声を再生
    st.audio(uploaded_file, format=uploaded_file.type)

    # 説明ボタン
    if st.button("音声を説明"):
        with st.spinner("分析中..."):
            # 音声データを読み込む
            audio_bytes = uploaded_file.read()

            # Gemini APIクライアント初期化
            api_key = os.environ.get("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)

            # リクエスト作成
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        types.Part.from_text(text="この音声について説明してください。"),
                    ],
                ),
            ]

            # APIを呼び出して説明を生成
            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=contents,
                config=types.GenerateContentConfig(),
            )

            # 結果を表示
            st.success("説明:")
            st.write(response.text)
