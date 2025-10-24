import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt
import numpy as np

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
ws = client.open("soccer_training").worksheet("シート1")

# --- データ読み込み ---
data = ws.get_all_records()
df = pd.DataFrame(data)

# --- 日付処理と空白除去 ---
df = df[df["日付"].astype(str).str.strip() != ""]
df["日付"] = pd.to_datetime(df["日付"], errors="coerce")

# --- リフティングレベル補完 ---
if "リフティングレベル" not in df.columns:
    df["リフティングレベル"] = None
df["リフティングレベル"] = df["リフティングレベル"].ffill()
if df["リフティングレベル"].isna().all():
    df["リフティングレベル"] = 1

# --- 不要列 ---
exclude_cols = ["メモ", "年齢", "疲労度"]
valid_cols = [c for c in df.columns if c not in exclude_cols + ["日付", "リフティングレベル"]]

# --- タイム系定義 ---
time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]

# --- 💪 最高記録計算 ---
best_list = []
for event in valid_cols:
    # リフティングだけ最新レベルで絞る
    if event == "リフティング時間":
        latest_level = df["リフティングレベル"].dropna().iloc[-1] if df["リフティングレベル"].notna().any() else 1
        target = df[df["リフティングレベル"] == latest_level]
    else:
        target = df.copy()

    # 数値化
    series = pd.to_numeric(target[event], errors="coerce").dropna()
    if series.empty:
        best_value = None
    elif event in time_events:
        best_value = series.min()
    else:
        best_value = series.max()
    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)
best_df["最高記録"] = pd.to_numeric(best_df["最高記録"], errors="coerce").round(2)

# --- 年齢を取得 ---
try:
    current_age = int(df["年齢"].dropna().astype(str).str.extract(r"(\d+)")[0].iloc[-1])
except Exception:
    current_age = None

# --- 基準値・目標値を取得 ---
base_dict, goal_dict = {}, {}
if current_age:
    ws_base = client.open("soccer_training").worksheet("基準値")
    ws_goal = client.open("soccer_training").worksheet("目標値")
    df_base = pd.DataFrame(ws_base.get_all_records())
    df_goal = pd.DataFrame(ws_goal.get_all_records())

    if not df_base.empty and current_age in df_base["年齢"].values:
        base_row = df_base[df_base["年齢"] == current_age].iloc[0]
        base_dict = base_row.drop("年齢").to_dict()
    if not df_goal.empty and current_age in df_goal["年齢"].values:
        goal_row = df_goal[df_goal["年齢"] == current_age].iloc[0]
        goal_dict = goal_row.drop("年齢").to_dict()

    best_df["基準値"] = best_df["種目"].map(base_dict)
    best_df["目標値"] = best_df["種目"].map(goal_dict)

# --- 書式統一 ---
best_df = best_df.round(2)

# --- 色付け ---
def highlight_rows(row):
    try:
        best, base, goal, event = row["最高記録"], row.get("基準値"), row.get("目標値"), row["種目"]
        if pd.isna(best) or pd.isna(base) or pd.isna(goal):
            return [""] * len(row)
        if event in time_events:  # タイム系（小さいほど良い）
            if best <= goal:
                color = "background-color:#d8e8ff"
            elif best <= base:
                color = "background-color:#d8f5d8"
            else:
                color = "background-color:#ffd6d6"
        else:  # 通常系（大きいほど良い）
            if best < base:
                color = "background-color:#ffd6d6"
            elif best < goal:
                color = "background-color:#d8f5d8"
            else:
                color = "background-color:#d8e8ff"
        return [color] * len(row)
    except Exception:
        return [""] * len(row)

styled = best_df.style.apply(highlight_rows, axis=1).format(subset=["最高記録"], formatter="{:.2f}")

# --- 表表示 ---
st.markdown(f"## 🏆 {current_age if current_age else ''}歳 基準・目標付き最高記録")
st.dataframe(styled, use_container_width=True)

# --- グラフ表示 ---
st.markdown("## 📈 種目別 推移グラフ")
id_cols = ["日付"]
if "リフティングレベル" in df.columns:
    id_cols.append("リフティングレベル")

df_long = df.melt(
    id_vars=id_cols,
    value_vars=valid_cols,
    var_name="種目",
    value_name="記録"
)
df_long["日付"] = pd.to_datetime(df_long["日付"], errors="coerce")
df_long["記録"] = pd.to_numeric(df_long["記録"], errors="coerce")

selected_event = st.selectbox("グラフを見たい種目を選んでください👇", valid_cols, index=0)
chart_data = df_long[df_long["種目"] == selected_event].dropna(subset=["記録"])
chart_data = chart_data.sort_values("日付")

if not chart_data.empty:
    reverse = selected_event in time_events
    line = (
        alt.Chart(chart_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("日付:T", title="日付"),
            y=alt.Y("記録:Q", title="記録", scale=alt.Scale(reverse=reverse)),
            tooltip=["日付", "記録"]
        )
        .properties(height=400, width=900)
    )
    st.altair_chart(line, use_container_width=True)

st.caption("🕒 安定版 2025-10-22")
