# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="別アプリ v1", page_icon="✨", layout="wide")
st.title("✨ 別アプリ v1 (GitHub→Streamlit Cloud)")

st.sidebar.header("設定")
name = st.sidebar.text_input("お名前", value="ゲスト")

@st.cache_data
def load_demo(n=100):
    rng = np.random.default_rng(42)
    return pd.DataFrame({"x": np.arange(n), "y": rng.normal(0,1,n).cumsum()})

st.write(f"こんにちは、{name} さん！")
df = load_demo(365)
st.subheader("📈 折れ線グラフ")
st.line_chart(df.set_index("x")["y"])

st.subheader("🗂️ データ（先頭10行）")
st.dataframe(df.head(10), use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("CSV ダウンロード", data=csv, file_name="demo.csv", mime="text/csv")

st.caption("v1 / 最小構成。pages/ を追加して多機能化できます。")