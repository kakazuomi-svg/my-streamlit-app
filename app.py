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

# ★ この2行を追加 ★
headers = ws.row_values(1)  # 1行目（ヘッダー）を取得
df = df[headers]             # スプレッドシートと同じ列順に並べ替え

st.dataframe(df)

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

# --- シートの列順どおりに並べ替え ---
headers = ws.row_values(1)
# シートの列順のうち、exclude_cols以外＋best_dfに存在する列のみ使用
column_order = [c for c in headers if c in best_df["種目"].values and c not in exclude_cols]

best_df["種目"] = pd.Categorical(best_df["種目"], categories=column_order, ordered=True)
best_df = best_df.sort_values("種目").reset_index(drop=True)

# --- 表示 ---
st.subheader("🏆 種目別 最高記録一覧（タイム系は最小値）")
st.dataframe(best_df, use_container_width=True)


# DataFrame の列をこの順に並べ替え（存在する列だけ抽出）
df = df[[col for col in column_order if col in df.columns]]
# --- 表示 ---
st.dataframe(best_df.sort_values("種目").reset_index(drop=True), use_container_width=True)





