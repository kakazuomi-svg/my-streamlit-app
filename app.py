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

        if np.isnan(best) or np.isnan(base) or np.isnan(goal):
            return [""] * len(row)

        # タイム系（小さいほど良い）
        if event in ["4mダッシュ", "50m走", "1.3km"]:
            if best > base:  # 基準より遅い
                color = "background-color: #ffd6d6;"  # パステルレッド
            elif best > goal:  # 目標よりは遅いけど基準内
                color = "background-color: #d8f5d8;"  # パステルグリーン
            else:  # 目標より速い（良い）
                color = "background-color: #d8e8ff;"  # パステルブルー
        else:
            # 通常系（大きいほど良い）
            if best < base:
                color = "background-color: #ffd6d6;"  # パステルレッド
            elif best < goal:
                color = "background-color: #d8f5d8;"  # パステルグリーン
            else:
                color = "background-color: #d8e8ff;"  # パステルブルー

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



