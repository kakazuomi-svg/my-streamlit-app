import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

st.title("🏃‍♀️ 種目別ベスト一覧（スプレッドシート連動版）")

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Streamlit CloudのSecretsから直接JSONを読み込む
creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

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

# --- シート読み込み ---
df = pd.DataFrame(ws.get_all_records())

# ここでは列名が「種目」「最高記録」「基準値」「目標値」になっている想定
# 存在しない場合は新規に作る
for col in ["種目", "最高記録", "基準値", "目標値"]:
    if col not in df.columns:
        df[col] = ""

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
