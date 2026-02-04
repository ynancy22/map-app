import streamlit as st
import os
import create_map_poster
from create_map_poster import create_poster, load_theme, get_coordinates

# 網頁配置
st.set_page_config(page_title="MapToPoster Web", page_icon="📍")
st.title("📍 MapToPoster 網頁版")
st.write("輸入城市與國家，生成專屬的極簡風格地圖海報。")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🎨 海報自訂選項")
    
    # 1. 城市與國家輸入
    city = st.text_input("城市名稱 (City)", "Taipei")
    city_size_opt = st.selectbox("城市文字大小", ["小", "中", "大"], index=1)
    
    country = st.text_input("國家名稱 (Country)", "Taiwan")
    country_size_opt = st.selectbox("國家文字大小", ["小", "中", "大"], index=1)
    
    # 2. 客製化紀念文字
    custom_text = st.text_input("紀念文字 (選填)", placeholder="例如：Our First Date / 2026.02.14")
    custom_text_size = st.slider("紀念文字大小", 10, 40, 18)

    st.divider()

    # 3. 地圖半徑控制 (結合輸入框與滑桿)
    st.write("地圖半徑 (Meters)")
    dist_input = st.number_input("直接輸入數值", value=10000, step=500)
    distance_slider = st.select_slider(
        "或是選擇定點",
        options=[2000, 5000, 10000, 15000, 20000],
        value=10000
    )
    # 若輸入框數值被變動過，則優先採用輸入框
    final_dist = dist_input if dist_input != 10000 else distance_slider

    # 4. 線條粗細
    line_width_opt = st.select_slider("線條粗細", options=["細", "標準", "粗"], value="標準")

    st.divider()

    # 5. 主題選擇
    theme_folder = 'themes'
    available_themes = []
    if os.path.exists(theme_folder):
        available_themes = [f.replace('.json', '') for f in os.listdir(theme_folder) if f.endswith('.json')]
    
    if not available_themes:
        available_themes = ["terracotta"] 
    
    selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=0)

# --- 轉換選單數值為比例係數 ---
size_map = {"小": 0.7, "中": 1.0, "大": 1.4}
line_map = {"細": 0.6, "標準": 1.0, "粗": 1.6}

# --- 初始化 Session State ---
if 'poster_path' not in st.session_state:
    st.session_state.poster_path = None

# --- 生成按鈕 ---
if st.button("開始生成海報"):
    with st.spinner("正在處理數據並繪圖，這可能需要一分鐘，請稍候..."):
        try:
            coords = get_coordinates(city, country)
            create_map_poster.THEME = load_theme(selected_theme)
            
            if not os.path.exists("posters"):
                os.makedirs("posters")
