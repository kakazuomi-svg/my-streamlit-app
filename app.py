import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.title("🏃‍♀️ 種目別ベスト一覧（スプレッドシート連動版）")

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Streamlit Secretsから直接辞書として取得
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)

client = gspread.authorize(creds)
ws = client.open("soccer_training").worksheet("シート1")



# --- 対象種目 ---
events = [
    "4mダッシュ",
    "50m走",
    "1.3km",
    "立ち幅跳び",
    "握力（右）",
    "握力（左）",
    "パントキック",
    "ゴールキック",
    "ソフトボール投げ",
]

# 空シート対策
if df.empty:
    st.warning("まだデータがありません。")
    st.stop()

# --- 横型 → 縦型に変換 ---
# 「日付」列を除く全ての列を melt で縦にまとめる
df_long = df.melt(id_vars=["日付"], var_name="種目", value_name="記録")

# 数値変換（文字列や空白を除外）
df_long["記録"] = pd.to_numeric(df_long["記録"], errors="coerce")

# --- 種目ごとに最大値を抽出 ---
best_df = df_long.groupby("種目", as_index=False)["記録"].max()

# --- 表示 ---
st.subheader("🏆 種目別 最高記録一覧")
st.dataframe(best_df, use_container_width=True)

# --- スプレッドシート読み込み ---
df = pd.DataFrame(ws.get_all_records())

# --- 種目が存在しないならスキップ ---
if df.empty:
    st.warning("まだデータがありません。")
    st.stop()

# --- 各種目ごとに「最高記録」抽出 ---
# ここでは「大きい方が良い」想定（例：立ち幅跳び、握力など）
# もし「タイム（短い方が良い）」の種目がある場合は、あとで条件分けできる
best_df = df.groupby("種目", as_index=False)["最高記録"].max()

# --- 表示 ---
st.subheader("🏆 種目別 最高記録一覧")
st.dataframe(best_df, use_container_width=True)




# --- 必要な種目だけ抽出 ---
df = df[df["種目"].isin(events)].copy()

# --- サイドバー入力 ---
st.sidebar.header("📏 基準値・目標値の設定")
for i, row in df.iterrows():
    base = st.sidebar.number_input(f"{row['種目']} 基準値", value=float(row["基準値"]) if row["基準値"] else 0.0, step=0.1, key=f"base_{i}")
    target = st.sidebar.number_input(f"{row['種目']} 目標値", value=float(row["目標値"]) if row["目標値"] else 0.0, step=0.1, key=f"target_{i}")
    df.at[i, "基準値"] = base
    df.at[i, "目標値"] = target

# --- 表表示 ---
st.dataframe(df[["種目", "最高記録", "基準値", "目標値"]], use_container_width=True)

# --- 保存ボタン ---
if st.button("💾 スプレッドシートに保存"):
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist(), value_input_option="USER_ENTERED")
    st.success("スプレッドシートに保存しました！")
