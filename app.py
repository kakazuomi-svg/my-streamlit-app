import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import altair as alt

# --- Google認証 ---
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)
ws = client.open("soccer_training").worksheet("シート1")

# --- データ読み込み ---
data = ws.get_all_records()
df = pd.DataFrame(data)

# --- 最新の年齢を取得（空欄スキップして最後の数字を拾う） ---
try:
    current_age = int(
        df["年齢"]
        .dropna()
        .astype(str)
        .str.extract(r"(\d+)")[0]
        .dropna()
        .iloc[-1]
    )
except Exception:
    current_age = None

# --- 最新年齢とリフティングレベルを安全に取得 ---
latest_age = None
if "年齢" in df.columns:
    tmp = df["年齢"].dropna().astype(str).str.extract(r"(\d+)")[0].dropna()
    if len(tmp) > 0:
        latest_age = tmp.iloc[-1]

latest_level = None
if "リフティングレベル" in df.columns:
    tmp = df["リフティングレベル"].dropna().astype(str)
    if len(tmp) > 0:
        latest_level = tmp.iloc[-1]

# --- 💪最高記録テーブル生成（リフティングだけレベル対応） ---
best_list = []
time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]

for event in valid_cols:
    # 全データ対象（空欄は除外）
    values = pd.to_numeric(df[event], errors="coerce").dropna()
    if values.empty:
        best_value = None
    elif event in time_events:
        best_value = values.min()  # タイム系：小さい方が良い
    else:
        best_value = values.max()  # 通常：大きい方が良い

    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)

# --- 基準値・目標値をマッピング ---
if current_age:
    ws_base = client.open("soccer_training").worksheet("基準値")
    ws_goal = client.open("soccer_training").worksheet("目標値")

    df_base = pd.DataFrame(ws_base.get_all_records())
    df_goal = pd.DataFrame(ws_goal.get_all_records())

    base_row = df_base[df_base["年齢"] == current_age].iloc[0]
    goal_row = df_goal[df_goal["年齢"] == current_age].iloc[0]

    base_dict = {k.strip(): v for k, v in base_row.drop(labels=["年齢"]).to_dict().items()}
    goal_dict = {k.strip(): v for k, v in goal_row.drop(labels=["年齢"]).to_dict().items()}

    best_df["種目"] = best_df["種目"].str.strip()
    best_df["基準値"] = best_df["種目"].map(base_dict)
    best_df["目標値"] = best_df["種目"].map(goal_dict)

# --- 数値を丸めて整形 ---
for col in ["最高記録", "基準値", "目標値"]:
    best_df[col] = pd.to_numeric(best_df[col], errors="coerce").round(2)


# --- 種目の順番を再指定 ---
best_df["種目"] = pd.Categorical(best_df["種目"], categories=column_order, ordered=True)
best_df = best_df.sort_values("種目", key=lambda x: x.map(order_map)).reset_index(drop=True)

import numpy as np


# --- 色付け関数（行ごと色分け・タイム系逆判定対応） ---
def highlight_rows(row):
    try:
        best = row["最高記録"]
        base = row["基準値"]
        goal = row["目標値"]
        event = row["種目"]

        if pd.isna(best) or pd.isna(base) or pd.isna(goal):
            return [""] * len(row)

        # タイム系（小さいほど良い）
        if event in ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]:
            if best < goal:
                color = "background-color: #d8e8ff;"  # パステルブルー（目標達成）
            elif best < base:
                color = "background-color: #d8f5d8;"  # パステルグリーン（基準クリア）
            else:
                color = "background-color: #ffd6d6;"  # パステルレッド（基準未達）

        else:
            # 通常系（大きいほど良い）
            if best < base:
                color = "background-color: #ffd6d6;"  # パステルレッド（基準未達）
            elif best < goal:
                color = "background-color: #d8f5d8;"  # パステルグリーン（基準クリア）
            else:
                color = "background-color: #d8e8ff;"  # パステルブルー（目標達成）

        # 行全体に適用
        return [color] * len(row)

    except Exception:
        return [""] * len(row)

        
# --- スタイル適用 ---
styled = (
    best_df.style
    .apply(highlight_rows, axis=1)
    .format(subset=["最高記録", "基準値", "目標値"], formatter="{:.2f}")
)

# --- 表示 ---
st.markdown(f"## 🏆 {current_age}歳 基準・目標付き最高記録一覧（タイム系は最小値）")
st.dataframe(styled, use_container_width=True)

# --- グラフ表示セクション（ここから追記！） ---
st.markdown("## 📈 種目別 推移グラフ")

# ドロップダウンで選択
selected_event = st.selectbox(
    "グラフを見たい種目を選んでください👇",
    [c for c in column_order if c in df_long["種目"].unique()],
    index=0
)

# 選択されたデータ抽出
chart_data = df_long[df_long["種目"] == selected_event].copy()
chart_data = chart_data.sort_values("日付")

# 日付をdatetime型に変換
chart_data["日付"] = pd.to_datetime(chart_data["日付"], errors="coerce")

# 日付順にソート
chart_data = chart_data.sort_values("日付")


import altair as alt

# --- 折れ線グラフ描画（Altair版） ---
import altair as alt

if not chart_data.empty:
    chart_data["日付"] = pd.to_datetime(chart_data["日付"], errors="coerce")
    chart_data["記録"] = pd.to_numeric(chart_data["記録"], errors="coerce")
    chart_data = chart_data.dropna(subset=["記録"])
    # 🩵ここに差し替え！
    # --- X軸範囲設定 ---
    if selected_event == "リフティング時間":
        x_min = pd.Timestamp("2025-04-01") - pd.DateOffset(months=4)
        x_max = pd.Timestamp("2028-03-31") + pd.DateOffset(months=4)
    else:
        x_min = pd.Timestamp("2025-04-01")
        x_max = pd.Timestamp("2028-03-31")
    x_domain = [x_min, x_max]

    
    # --- タイム系は反転Y軸に ---
    time_events = ["4mダッシュ", "50m走", "1.3km"]
    reverse_scale = True if selected_event in time_events else False

    # --- 表示ライン選択 ---
    line_type = st.selectbox("表示するラインを選んでください👇", ["なし", "基準値", "目標値"], index=2)

    # --- 年齢別の色設定 ---
    colors = {10: "#66bb6a", 11: "#ffa726", 12: "#ef5350"}  # 緑, オレンジ, 赤

    # --- 折れ線（記録推移） ---


if not chart_data.empty:
    chart_data["日付"] = pd.to_datetime(chart_data["日付"], errors="coerce")
    chart_data["記録"] = pd.to_numeric(chart_data["記録"], errors="coerce")
    chart_data = chart_data.dropna(subset=["記録"])

    # --- X軸範囲設定（リフティングはデータ期間にズーム＋余白） ---
    if selected_event == "リフティング時間":
        dmin = chart_data["日付"].min()
        dmax = chart_data["日付"].max()
        # データの最小最大に前後2ヶ月の余白を足す
        x_min = (dmin - pd.DateOffset(months=2))
        x_max = (dmax + pd.DateOffset(months=2))
        chart_width = 1200   # リフティングは横幅も広めに
    else:
        x_min = pd.Timestamp("2025-04-01")
        x_max = pd.Timestamp("2028-03-31")
        chart_width = 900    # 通常の幅

    x_domain = [x_min, x_max]

    # --- タイム系は反転Y軸に ---
    time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]
    reverse_scale = True if selected_event in time_events else False

    # --- 表示ライン選択 ---
    line_type = st.selectbox(
        "表示するラインを選んでください👇",
        ["なし", "基準値", "目標値"],
        index=2,
        key="line_type_main"
    )

    # --- 📈 折れ線（スムージング＋点） ---
    line = (
        alt.Chart(chart_data)
        .mark_line(
            point=alt.OverlayMarkDef(size=40),
            interpolate="monotone",
            color="#1f77b4",
            size=2
        )
        .encode(
            x=alt.X(
                "日付:T",
                title="日付（年月）",
                scale=alt.Scale(domain=x_domain),
                axis=alt.Axis(format="%Y年%m月", labelAngle=-40)
            ),
            y=alt.Y(
                "記録:Q",
                title="記録",
                scale=alt.Scale(zero=False, reverse=reverse_scale)
            ),
            tooltip=[
                alt.Tooltip("yearmonthdate(日付):T", title="日付", format="%Y年%m月%d日"),
                alt.Tooltip("記録:Q", title="記録")
            ]
        )
        .properties(height=400, width=chart_width)
    )


    # --- レイヤー作成 ---
    layers = [line]

    # --- ライン（基準値 or 目標値） ---
    if line_type == "基準値":
        for age in [10, 11, 12]:
            base_row = df_base[df_base["年齢"] == age]
            if not base_row.empty and selected_event in base_row.columns:
                val = pd.to_numeric(base_row[selected_event], errors="coerce").values[0]
                df_tmp = pd.DataFrame({"基準値": [val]})
                base_line = (
                    alt.Chart(df_tmp)
                    .mark_rule(color=colors[age], strokeDash=[6, 4], size=2)
                    .encode(y=alt.Y("基準値:Q"))
                )
                layers.append(base_line)

    elif line_type == "目標値":
        for age in [10, 11, 12]:
            goal_row = df_goal[df_goal["年齢"] == age]
            if not goal_row.empty and selected_event in goal_row.columns:
                val = pd.to_numeric(goal_row[selected_event], errors="coerce").values[0]
                df_tmp = pd.DataFrame({"目標値": [val]})
                goal_line = (
                    alt.Chart(df_tmp)
                    .mark_rule(color=colors[age], strokeDash=[6, 4], size=2)
                    .encode(y=alt.Y("目標値:Q"))
                )
                layers.append(goal_line)

    # --- 結合＆表示 ---
    chart = alt.layer(*layers)
    st.altair_chart(chart, use_container_width=True)
