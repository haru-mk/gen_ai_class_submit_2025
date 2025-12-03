import os
import json
import streamlit as st
from google import genai
from google.genai import types

# ページ設定
st.set_page_config(page_title="俳句ジェネレーター", page_icon="🌸")

# タイトル
st.title("🌸 俳句ジェネレーター")
st.write("テキストを入力すると、AIが俳句を作成します")

# テキスト入力
input_text = st.text_area(
    "テキストを入力してください",
    placeholder="例: 春の訪れとともに、桜の花が咲き始めました。",
    height=100
)

# 生成ボタン
if st.button("俳句を生成", type="primary"):
    if not input_text:
        st.warning("テキストを入力してください")
    else:
        with st.spinner("俳句を作成中..."):
            try:
                # APIキー取得
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    st.error("GEMINI_API_KEYが設定されていません")
                    st.stop()

                # クライアント初期化
                client = genai.Client(api_key=api_key)

                # プロンプト作成
                contents = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text=f"次のテキストについて俳句を作成してください:\n{input_text}\n出力はJSON形式{{'haiku': 'ここに俳句','kigo': '春or夏or秋or冬or不明'}}です。他の情報は含めないでください。"
                            ),
                        ],
                    ),
                ]

                # API呼び出し
                response = client.models.generate_content(
                    model="gemini-flash-lite-latest",
                    contents=contents,
                    config=types.GenerateContentConfig(),
                )

                # JSONパース（マークダウン形式に対応）
                response_text = response.text.strip()
                if response_text.startswith("```"):
                    lines = response_text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    response_text = "\n".join(lines)

                haiku_data = json.loads(response_text)
                haiku = haiku_data.get("haiku", "")
                kigo = haiku_data.get("kigo", "不明")

                # 季節ごとの色設定
                season_colors = {
                    "春": "#FFB7C5",  # ピンク
                    "夏": "#87CEEB",  # スカイブルー
                    "秋": "#FF8C00",  # ダークオレンジ
                    "冬": "#FFFFFF",  # パウダーブルー
                    "不明": "#A9A9A9"  # グレー
                }

                color = season_colors.get(kigo, "#A9A9A9")

                # 結果表示
                st.success("生成完了！")
                st.markdown(f"### 季語: {kigo}")
                st.markdown(
                    f'<div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center;">'
                    f'<h2 style="color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">{haiku}</h2>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            except json.JSONDecodeError as e:
                st.error(f"JSONパースエラー: {e}")
                st.code(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

