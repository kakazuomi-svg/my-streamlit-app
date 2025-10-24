import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)

# --- シート読込 ---
ws = client.open("soccer_training").worksheet("シート1")
data = ws.get_all_records()
df = pd.DataFrame(data)

# --- 列順合わせ ---
headers = ws.row_values(1)
df = df[headers]

# --- 不要列除外 ---
exclude_cols = ["メモ", "年齢", "疲労度", "リフティングレベル"]
valid_cols = [c for c in df.columns if c not in exclude_cols + ["日付"]]

# --- 数値変換 ---
for c in valid_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# --- タイム系定義 ---
time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]

# --- 💪 各項目の最高記録（or最小）を算出 ---
best_list = []
for event in valid_cols:
    series = df[event].dropna()
    if series.empty:
        best_value = None
    elif event in time_events:
        best_value = series.min()  # タイム系は小さいほど良い
    else:
        best_value = series.max()  # 通常は大きいほど良い
    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)

# --- 最新の年齢を取得 ---
try:
    current_age = int(
        df["年齢"].dropna().astype(str).str.extract(r"(\d+)")[0].dropna().iloc[-1]
    )
except Exception:
    current_age = None

# --- 基準値・目標値を読込 ---
if current_age:
    ws_base = client.open("soccer_training").worksheet("基準値")
    ws_goal = client.open("soccer_training").worksheet("目標値")
    df_base = pd.DataFrame(ws_base.get_all_records())
    df_goal = pd.DataFrame(ws_goal.get_all_records())
    base_row = df_base[df_base["年齢"] == current_age].iloc[0]
    goal_row = df_goal[df_goal["年齢"] == current_age].iloc[0]
    base_dict = base_row.drop(labels=["年齢"]).to_dict()
    goal_dict = goal_row.drop(labels=["年齢"]).to_dict()
    best_df["基準値"] = best_df["種目"].map(base_dict)
    best_df["目標値"] = best_df["種目"].map(goal_dict)
else:
    best_df["基準値"] = None
    best_df["目標値"] = None

# --- 小数点統一 ---
for col in ["最高記録", "基準値", "目標値"]:
    best_df[col] = pd.to_numeric(best_df[col], errors="coerce").round(2)

# --- 色付け関数 ---
def highlight_rows(row):
    try:
        best, base, goal, event = row["最高記録"], row["基準値"], row["目標値"], row["種目"]
        if pd.isna(best) or pd.isna(base) or pd.isna(goal):
            return [""] * len(row)
        if event in time_events:
            if best < goal:
                color = "background-color: #d8e8ff;"
            elif best < base:
                color = "background-color: #d8f5d8;"
            else:
                color = "background-color: #ffd6d6;"
        else:
            if best < base:
                color = "background-color: #ffd6d6;"
            elif best < goal:
                color = "background-color: #d8f5d8;"
            else:
                color = "background-color: #d8e8ff;"
        return [color] * len(row)
    except Exception:
        return [""] * len(row)

# --- 表表示 ---
st.markdown(f"## 🏆 {current_age or ''}歳 最高記録一覧（タイム系は最小）")
st.dataframe(best_df.style.apply(highlight_rows, axis=1), use_container_width=True)

# --- グラフ ---
st.markdown("## 📈 種目別 推移グラフ")
df_long = df.melt(id_vars=["日付"], value_vars=valid_cols, var_name="種目", value_name="記録")
selected_event = st.selectbox("グラフを見たい種目を選んでください👇", valid_cols)
chart_data = df_long[df_long["種目"] == selected_event].dropna()
chart_data["日付"] = pd.to_datetime(chart_data["日付"], errors="coerce")
reverse_scale = selected_event in time_events

line = (
    alt.Chart(chart_data)
    .mark_line(point=True, interpolate="monotone")
    .encode(
        x=alt.X("日付:T", title="日付"),
        y=alt.Y("記録:Q", title="記録", scale=alt.Scale(reverse=reverse_scale, zero=False)),
        tooltip=["日付", "記録"],
    )
    .properties(width=900, height=400)
)
st.altair_chart(line, use_container_width=True)

