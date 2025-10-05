import streamlit as st
import pandas as pd

st.title("🏃‍♀️ 種目別ベスト一覧")

# 種目リスト（リフティング除外）
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

# ダミーデータ（後でシート連携に置き換え予定）
data = []
for e in events:
    row = {
        "種目": e,
        "最高記録": 0,
        "基準値": 0,
        "目標値": 0,
    }
    data.append(row)

df = pd.DataFrame(data, columns=["種目", "最高記録", "基準値", "目標値"])

st.dataframe(df, use_container_width=True)
