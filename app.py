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

# --- 列順をスプレッドシートと合わせる ---
headers = ws.row_values(1)
df = df[headers]

# --- 不要な列を除外 ---
exclude_cols = ["メモ", "年齢", "リフティングレベル", "疲労度"]
cols_to_use = [c for c in df.columns if c not in exclude_cols]

# --- 横型 → 縦型に変換 ---
df_long = df.melt(
    id_vars=["日付"],
    value_vars=[c for c in cols_to_use if c != "日付"],
    var_name="種目",
    value_name="記録"
)

# --- 💡ここに追加！（リフティング時間変換） ---
def convert_min_dot_sec(x):
    try:
        x = str(x).strip()
        if "." in x:
            mins, secs = x.split(".")
            mins = int(mins)
            secs = int(secs)
            return mins + secs / 60
        else:
            return float(x)
    except:
        return None

# リフティング時間だけ変換（例：15.30 → 15.5）
df_long.loc[df_long["種目"] == "リフティング時間", "記録"] = (
    df_long.loc[df_long["種目"] == "リフティング時間", "記録"].apply(convert_min_dot_sec)
)

# --- 数値変換 ---
df_long["記録"] = pd.to_numeric(df_long["記録"], errors="coerce")

# --- タイム系（小さい方が良い） ---
time_events = ["1.3km", "4mダッシュ", "50m走", "リフティング時間"]

# --- 💪最高記録算出 ---
# 対象列を定義
valid_cols = [c for c in df.columns if c not in ["日付", "メモ", "年齢", "疲労度", "リフティングレベル"]]
best_list = []

# 最新レベルの取得（リフティング用）
latest_level = (
    df["リフティングレベル"].dropna().iloc[-1]
    if "リフティングレベル" in df.columns and df["リフティングレベル"].notna().any()
    else 1
)

# タイム系（小さいほど良い）
time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]

# 各種目をループ
for event in valid_cols:

    # 🟡 リフティング時間 → 最新レベル内の最小値
    if event == "リフティング時間":
        target = df[df["リフティングレベル"] == latest_level]
        values = pd.to_numeric(target[event], errors="coerce").dropna()
        best_value = values.min() if not values.empty else None

    # 🟢 タイム系（全期間から最小値）
    elif event in time_events:
        values = pd.to_numeric(df[event], errors="coerce").dropna()
        best_value = values.min() if not values.empty else None

    # 🟢 通常系（全期間から最大値）
    else:
        values = pd.to_numeric(df[event], errors="coerce").dropna()
        best_value = values.max() if not values.empty else None

    best_list.append({"種目": event, "最高記録": best_value})

# --- best_df 作成 ---
best_df = pd.DataFrame(best_list)
best_df = pd.DataFrame()

# 記録種目（＝日付やメモなどを除外）
exclude_cols = ["日付", "年齢", "身長", "体重", "疲労度", "メモ"]
event_cols = [c for c in df.columns if c not in exclude_cols]

time_events = ["4mダッシュ", "50m走", "1.3km"]
lifting_event = "リフティング時間"

for event in event_cols:
    sub = pd.to_numeric(df[event], errors="coerce").dropna()
    if len(sub) == 0:
        continue

    # 判定ルール
    if event in time_events:
        best_val = sub.min()  # 小さいほど良い
    elif event == lifting_event:
        best_val = sub.iloc[-1]  # リフティングは最新レベル記録
    else:
        best_val = sub.max()  # それ以外は大きいほど良い（距離・力など）

    best_df = pd.concat([
        best_df,
        pd.DataFrame({"種目": [event], "最高記録": [best_val]})
    ], ignore_index=True)



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

# --- 基準値・目標値シートを読み込み ---
base_dict, goal_dict = {}, {}

if current_age:
    ws_base = client.open("soccer_training").worksheet("基準値")
    ws_goal = client.open("soccer_training").worksheet("目標値")

    df_base = pd.DataFrame(ws_base.get_all_records())
    df_goal = pd.DataFrame(ws_goal.get_all_records())

    # 年齢に該当する行を取得
    base_row = df_base[df_base["年齢"] == current_age].iloc[0]
    goal_row = df_goal[df_goal["年齢"] == current_age].iloc[0]

    base_dict = base_row.drop(labels=["年齢"]).to_dict()
    goal_dict = goal_row.drop(labels=["年齢"]).to_dict()

    # --- best_df に基準値・目標値を追加 ---
    best_df["基準値"] = best_df["種目"].map(base_dict)
    best_df["目標値"] = best_df["種目"].map(goal_dict)

# --- タイトル書式統一（None回避） ---
title_age = f"{current_age}歳 " if current_age else ""

# --- 並び順マップを作る ---
headers = ws.row_values(1)
column_order = [c for c in headers if c in best_df["種目"].values and c not in exclude_cols]
order_map = {v: i for i, v in enumerate(column_order)}

# --- 書式を小数点2位に統一 ---
for col in ["最高記録", "基準値", "目標値"]:
    if col in best_df.columns:
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

# --- 表示（タイトルも統一） ---
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

# --- 折れ線グラフ描画（Altair版） ---
if not chart_data.empty:
    chart_data["日付"] = pd.to_datetime(chart_data["日付"], errors="coerce")
    chart_data["記録"] = pd.to_numeric(chart_data["記録"], errors="coerce")
    chart_data = chart_data.dropna(subset=["記録"])

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
            x_min = (dmin - pd.DateOffset(months=2))
            x_max = (dmax + pd.DateOffset(months=2))
            chart_width = 1200
        else:
            x_min = pd.Timestamp("2025-04-01")
            x_max = pd.Timestamp("2028-03-31")
            chart_width = 900

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
