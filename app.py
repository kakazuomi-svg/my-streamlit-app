import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["google_service_account"], scopes=SCOPE)
client = gspread.authorize(creds)

ws = client.open("soccer_training").worksheet("シート1")
data = ws.get_all_records()
# ✅ 空白行を削除する（全列がNoneの行を除去）
data = [row for row in data if any(v not in [None, "", " "] for v in row.values())]
df = pd.DataFrame(data)

st.write("📊 読み込みデータ（上位5件）")
st.dataframe(df.head())

# 不要列除外
exclude_cols = ["メモ", "年齢", "疲労度", "リフティングレベル"]
valid_cols = [c for c in df.columns if c not in exclude_cols + ["日付"]]

# デバッグ出力
st.write("🎯 対象列:", valid_cols)

# 数値変換テスト
for c in valid_cols:
     # ここで文字列を安全に数値化（全角・空白・カンマ対応）
    df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    st.write(f"列 [{c}] 型:", df[c].map(type).unique())

# --- 最高記録（シンプル安定版：全データから算出） ---
time_events = ["4mダッシュ", "50m走", "1.3km", "リフティング時間"]

best_list = []
for event in [c for c in df.columns if c not in ["日付", "メモ", "疲労度", "年齢", "リフティングレベル"]]:
    # 数値変換（空白・カンマ対応）
    values = pd.to_numeric(df[event].astype(str).str.replace(",", "").str.strip(), errors="coerce").dropna()

    if values.empty:
        best_value = None
    elif event in time_events:
        best_value = values.min()   # タイム系 → 最小値
    else:
        best_value = values.max()   # それ以外 → 最大値

    best_list.append({"種目": event, "最高記録": best_value})

best_df = pd.DataFrame(best_list)
