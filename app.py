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

# --- シート読み込み ---
records = ws.get_all_records()

if not records:
    st.warning("まだデータがありません。")
    st.stop()

df = pd.DataFrame(records)

# --- 不要な列を除外 ---
exclude_cols = ["メモ", "年齢", "リフティングレベル", "リフティング時間", "身長", "体重"]
cols_to_use = [c for c in df.columns if c not in exclude_cols]

# --- meltで縦型に変換 ---
df_long = df.melt(
    id_vars=["日付"],
    value_vars=[c for c in cols_to_use if c != "日付"],
    var_name="種目",
    value_name="記録"
)

# 数値変換
df_long["記録"] = pd.to_numeric(df_long["記録"], errors="coerce")

# --- タイム系種目（最小値をとる） ---
time_events = ["1.3km", "4mダッシュ", "50m走"]

# --- 集計 ---
best_list = []
for event, group in df_long.groupby("種目"):
    if event in time_events:
        best_value = group["記録"].min()
    else:
        best_value = group["記録"].max()
    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)

# --- 表示 ---
st.subheader("🏆 種目別 最高記録一覧（タイム系は最小値）")
st.dataframe(best_df.sort_values("種目").reset_index(drop=True), use_container_width=True)

#----------------------------------------------------------------------------------------------

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
