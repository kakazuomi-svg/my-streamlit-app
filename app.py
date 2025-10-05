import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
ws = client.open("soccer_training").worksheet("シート1")

# --- データ読み込み ---
data = ws.get_all_records()
df = pd.DataFrame(data)

# --- 列順をスプレッドシートと合わせる ---
headers = ws.row_values(1)
df = df[headers]

# --- 不要な列を除外 ---
exclude_cols = ["メモ", "年齢", "リフティングレベル", "リフティング時間", "疲労度"]
cols_to_use = [c for c in df.columns if c not in exclude_cols]

# --- 横型 → 縦型に変換 ---
df_long = df.melt(
    id_vars=["日付"],
    value_vars=[c for c in cols_to_use if c != "日付"],
    var_name="種目",
    value_name="記録"
)

# --- 数値変換 ---
df_long["記録"] = pd.to_numeric(df_long["記録"], errors="coerce")

# --- タイム系（小さい方が良い） ---
time_events = ["1.3km", "4mダッシュ", "50m走"]

# --- 集計（最高記録） ---
best_list = []
for event, group in df_long.groupby("種目"):
    if event in time_events:
        best_value = group["記録"].min()
    else:
        best_value = group["記録"].max()
    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)


# --- 最新の年齢を取得（最後に入力された「数字」を使う） ---
try:
    current_age = int(df["年齢"].dropna().astype(str).str.extract(r'(\d+)').dropna().iloc[-1, 0])
except Exception:
    current_age = None

if current_age:
    # --- 基準値シート読み込み ---
    ws_base = client.open("soccer_training").worksheet("基準値")
    base_data = ws_base.get_all_records()
    df_base = pd.DataFrame(base_data)

    # --- 目標値シート読み込み ---
    ws_goal = client.open("soccer_training").worksheet("目標値")
    goal_data = ws_goal.get_all_records()
    df_goal = pd.DataFrame(goal_data)

    # 年齢で該当行を取得
    base_row = df_base[df_base["年齢"] == current_age].iloc[0]
    goal_row = df_goal[df_goal["年齢"] == current_age].iloc[0]

    # 「年齢」列を除いた列名でループ
    base_dict = base_row.drop(labels=["年齢"]).to_dict()
    goal_dict = goal_row.drop(labels=["年齢"]).to_dict()

    # --- best_df に基準値・目標値をマージ ---
    best_df["基準値"] = best_df["種目"].map(base_dict)
    best_df["目標値"] = best_df["種目"].map(goal_dict)

# --- 表示 ---
st.subheader(f"🏆 {current_age}歳 基準・目標付き最高記録一覧（タイム系は最小値）")
st.dataframe(best_df, use_container_width=True)

