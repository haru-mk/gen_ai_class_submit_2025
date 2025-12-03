import os
import streamlit as st
from google import genai
from google.genai import types

# ページ設定
st.title("画像説明アプリ")
st.write("画像をアップロードすると、AIが説明してくれます")

# サンプル画像のダウンロードボタン
if os.path.exists("sample.png"):
    with open("sample.png", "rb") as f:
        sample_image_bytes = f.read()
    st.download_button(
        label="サンプル画像をダウンロード",
        data=sample_image_bytes,
        file_name="sample.png",
        mime="image/png",
    )

# 画像アップロード
uploaded_file = st.file_uploader("画像を選択してください", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # アップロードされた画像を表示
    st.image(uploaded_file, caption="アップロードされた画像", width="stretch")

    # 説明ボタン
    if st.button("画像を説明"):
        with st.spinner("分析中..."):
            # 画像データを読み込む
            image_bytes = uploaded_file.read()

            # Gemini APIクライアント初期化
            api_key = os.environ.get("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)

            # リクエスト作成
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        types.Part.from_text(text="この画像について説明してください。"),
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
