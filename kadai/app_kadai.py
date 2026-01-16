import os
import sqlite3
from datetime import datetime
import time
import streamlit as st
from google import genai

# ページ設定
st.set_page_config(page_title="ゲーム提案 AI", page_icon="🎮", layout="wide")

# カスタムCSS（フォントはそのまま、色・カード・ボタンをゲーム風に調整）
st.markdown(
    """
    <style>
    /* 背景 */
    .reportview-container, .main, .block-container {
        background: linear-gradient(180deg, #0f1724 0%, #0b1020 60%);
        color: #e6eef8;
    }
    /* ヘッダー */
    .header {
        display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
    }
    .header .title { font-size: 34px; font-weight: 700; color: #ffd166; }
    .header .subtitle { color: #cfe8ff; opacity: 0.9; }

    /* ゲームカード */
    .game-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        display: flex;
        gap: 12px;
        align-items: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.6), inset 0 -2px 6px rgba(0,0,0,0.2);
    }
    .game-rank { width:36px; height:36px; border-radius:8px; background:#ff7f50; display:flex; align-items:center; justify-content:center; font-weight:700; color:#081123; }
    .game-name { font-size:18px; font-weight:700; color:#fff; }
    .game-desc { color:#d7e9ff; margin-top:6px; font-size:13px; }
    .game-links { margin-top:10px; }
    .link-btn {
        display:inline-block; padding:6px 10px; margin-right:8px; border-radius:8px; text-decoration:none; color:#071427; background:#ffd166;
        font-weight:600; font-size:13px;
    }
    .link-btn.secondary { background:#7dd3fc; color:#02293a; }
    .link-btn.tertiary { background:#a78bfa; color:#1b0b3a; }

    /* ボタン系の微調整（Streamlitの内部ボタン） */
    div.stButton > button {
        background: linear-gradient(180deg,#ffd166,#ffb84d) !important; color:#081123; font-weight:700; border: none; box-shadow: none;
    }

    /* 履歴のexpander内 */
    .stExpanderHeader { color:#ffd166; }
    /* 入力ラベル（テキスト入力・テキストエリアのラベル）を白にする */
    .stTextInput label, .stTextArea label, .stTextInput > label, .stTextArea > label, label[for] {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# カスタムヘッダー（タイトルの見た目をゲーム風に）
st.markdown('<div class="header">🎮 <div><div class="title">ゲーム提案 AI</div><div class="subtitle">あなたの気分にあったゲームを提案します</div></div></div>', unsafe_allow_html=True)

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


def generate_one_line_descriptions(titles, mood="", opinion=""):
    """Given a list of titles and optional mood/opinion, return descriptions in the same order.
    If mood/opinion are provided, include how the game matches them in the description.
    Returns a list of descriptions (same length as titles, padded with '説明なし' if missing).
    """
    if not titles:
        return []

    if mood or opinion:
        context = ""
        if mood and opinion:
            context = (
                f"ユーザーの気分：{mood}\n"
                f"ユーザーの好み：{opinion}\n\n"
                "以下のゲームタイトルについて、それぞれ1行で簡潔に説明してください。"
                "説明には、このゲームがなぜユーザーの気分と好みに合っているのかを含めてください。"
            )
        elif mood:
            context = (
                f"ユーザーの気分：{mood}\n\n"
                "以下のゲームタイトルについて、それぞれ1行で簡潔に説明してください。"
                "説明には、このゲームがなぜユーザーの気分に合っているのかを含めてください。"
            )
        else:
            context = (
                f"ユーザーの好み：{opinion}\n\n"
                "以下のゲームタイトルについて、それぞれ1行で簡潔に説明してください。"
                "説明には、このゲームがなぜユーザーの好みに合っているのかを含めてください。"
            )
        
        prompt = (
            context
            + " タイトルは出力せず、タイトルの順に対応する説明だけを改行区切りで出力してください。\n\n"
            + "\n".join(titles)
        )
    else:
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
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("あなたの気分や意見を教えてください")
with col2:
    st.caption("💡 どちらか片方を入力しても提案可能です")

mood = st.text_input("現在の気分は？ (例: 刺激が欲しい、興奮している、リラックスしたい)")
opinion = st.text_area("ゲームに関する意見やジャンルの好み (例: アクション好き、ストーリー重視、短時間プレイ)", height=100)

col_btn, col_info = st.columns([1, 4])
with col_btn:
    submit_button = st.button("ゲームを提案してもらう")
with col_info:
    st.caption("⚠️ 提案するゲームによってはSteamで販売されていないゲームが該当される場合もあります")

if submit_button:
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
            contents=f"""以下のユーザーの気分と意見を詳しく分析して、最も適切なゲームタイトルを20個提案してください。

{user_state_section}{prefs_section}

【提案の条件】
1. 実在するゲームのみを提案してください
2. 架空のゲームは絶対に含めないでください
3. 有名なゲームだけでなく、比較的知られていないが高い評価を受けているゲームも含めてください
4. 新作から懐かしい作品まで、様々な時期のゲームを提案してください
5. ユーザーの気分と意見を最大限に考慮してください
6. 各タイトルは改行で区切ってください
7. ゲームタイトルのみを出力してください（説明は不要）"""
        )
        suggested_games = response.text.strip().split('\n')
        # 空行を削除
        suggested_games = [game.strip() for game in suggested_games if game.strip()]

        # 各ゲームの一言説明を生成
        try:
            descriptions = generate_one_line_descriptions(suggested_games, mood, opinion)
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

        st.success("✨ おすすめゲーム（20件）:")
        for i, game in enumerate(suggested_games, 1):
            steam_url = f"https://store.steampowered.com/search/?term={game.replace(' ', '+')}"
            official_url = f"https://www.google.com/search?q={game.replace(' ', '+')}+official+website"
            youtube_url = f"https://www.youtube.com/results?search_query={game.replace(' ', '+')}+official+trailer"

            # カード表示（HTMLを使って見た目を調整）
            desc = descriptions[i-1] if i-1 < len(descriptions) else '説明なし'
            card_html = f'''
            <div class="game-card">
              <div class="game-rank">{i}</div>
              <div style="flex:1">
                <div class="game-name">{game}</div>
                <div class="game-desc">{desc}</div>
                <div class="game-links">
                  <a class="link-btn" href="{steam_url}" target="_blank">🔗 Steam</a>
                  <a class="link-btn secondary" href="{official_url}" target="_blank">🌐 公式</a>
                  <a class="link-btn tertiary" href="{youtube_url}" target="_blank">▶️ YouTube</a>
                </div>
              </div>
            </div>
            '''

            st.markdown(card_html, unsafe_allow_html=True)
            st.divider()
    else:
        st.warning("気分または意見のいずれかを入力してください")

# 提案履歴一覧
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("📋 提案履歴")
with col2:
    st.caption("🗑️ 削除ボタンはダブルクリックで利用できます")

conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT id, mood, opinion, suggested_game, created_at FROM game_suggestions ORDER BY created_at DESC").fetchall()
conn.close()

# セッション状態の初期化
if 'confirm_delete_all' not in st.session_state:
    st.session_state['confirm_delete_all'] = False

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

            # リンクの生成
            steam_url = f"https://store.steampowered.com/search/?term={game.replace(' ', '+')}"
            official_url = f"https://www.google.com/search?q={game.replace(' ', '+')}+official+website"
            youtube_url = f"https://www.youtube.com/results?search_query={game.replace(' ', '+')}+official+trailer"

            st.markdown(f"[🔗 Steam]({steam_url}) | [🌐 公式]({official_url}) | [▶️ YouTube]({youtube_url})")

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
