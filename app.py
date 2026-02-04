import streamlit as st
import os
import create_map_poster
from create_map_poster import create_poster, load_theme, get_coordinates

# 網頁配置
st.set_page_config(page_title="MapToPoster", page_icon="📍")
st.title("📍 MapToPoster")
st.write("網頁版地圖生成器")
st.write("輸入城市與國家，生成專屬的極簡風格地圖海報。")
st.write("Select a city and generate a stylish personalized map")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🎨 海報自訂選項 Options")
    
    city = st.text_input("城市 (City)", "Taipei")
    city_size_opt = st.selectbox("城市文字大小 font size", ["小 S", "中 M", "大 L"], index=1)
    
    country = st.text_input("國家 (Country)", "Taiwan")
    country_size_opt = st.selectbox("國家文字大小 font size", ["小 S", "中 M", "大 L"], index=1)
    
    # 客製化紀念文字
    custom_text = st.text_input("紀念文字 (選填) Customized text (optional)", placeholder="例如：Our First Date / 2019.02.14")
    custom_text_size = st.slider("紀念文字大小 font size", 10, 40, 18)

    st.divider()

    # 地圖半徑控制
    st.write("地圖半徑 (Meters)")
    distance_slider = st.select_slider(
        options=[2000, 4000, 6000, 8000, 10000, 15000, 20000],
        value=10000
    )
    final_dist = distance_slider

    # 線條粗細
    line_width_opt = st.selectbox("線條粗細 Line width", ["細 Light", "標準 Regular", "粗 Bold"], index=1)

    st.divider()

    # 主題選擇
    theme_folder = 'themes'
    available_themes = []
    if os.path.exists(theme_folder):
        available_themes = [f.replace('.json', '') for f in os.listdir(theme_folder) if f.endswith('.json')]
    
    if not available_themes:
        available_themes = ["terracotta"] 
    
    selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=0)

# 轉換比例係數
size_map = {"小 S": 0.7, "中 M": 1.0, "大 L": 1.4}
line_map = {"細 Light": 0.6, "標準 Regular": 1.0, "粗 Bold": 1.6}

# 初始化 Session State
if 'poster_path' not in st.session_state:
    st.session_state.poster_path = None

# --- 主畫面按鈕與 Source 標註 ---
st.divider()

# 按鈕居中對齊
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    generate_btn = st.button("GO!", use_container_width=True)

# 將 Source 放在按鈕正下方，不固定在視窗底部以避免語法報錯
# --- 頁面固定底部的來源標註 ---
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgba(0, 0, 0, 0.5); /* 半透明背景 */
        color: gray;
        text-align: center;
        padding: 10px 0;
        font-size: 0.8em;
        z-index: 999;
    }
    .footer a {
        color: #007bff;
        text-decoration: none;
    }
    /* 增加頁面底部內距，防止內容被 footer 遮擋 */
    .main .block-container {
        padding-bottom: 60px;
    }
    </style>
    <div class="footer">
    <span>Source:</span>
        <a href="https://github.com/originalankur/maptoposter" target="_blank">
            <img src="https://flat.badgen.net/badge/icon/github?icon=github&label=originalankur/maptoposter&color=black" alt="GitHub Source">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 生成邏輯 ---
if generate_btn:
    with st.spinner("正在處理數據並繪圖，請稍候... Processing..."):
        try:
            coords = get_coordinates(city, country)
            create_map_poster.THEME = load_theme(selected_theme)
            
            if not os.path.exists("posters"):
                os.makedirs("posters")
            
            output_file = f"posters/{city.replace(' ', '_')}_{selected_theme}.png"
            
            # 呼叫核心引擎
            create_poster(
                city=city,
                country=country,
                point=coords,
                dist=final_dist,
                output_file=output_file,
                output_format="png",
                city_scale=size_map[city_size_opt],
                country_scale=size_map[country_size_opt],
                line_scale=line_map[line_width_opt],
                custom_text=custom_text,
                custom_text_size=custom_text_size
            )
            st.session_state.poster_path = output_file
                
        except Exception as e:
            st.error(f"生成失敗 Error: {e}")

# --- 顯示與下載區塊 ---
if st.session_state.poster_path and os.path.exists(st.session_state.poster_path):
    st.divider()
    st.image(st.session_state.poster_path, caption=f"預覽 Preview：{city}")
    
    with open(st.session_state.poster_path, "rb") as file:
        st.download_button(
            label="💾 下載高解析度海報 Download Hi-res",
            data=file,
            file_name=f"{city}_poster.png",
            mime="image/png",
            use_container_width=True
        )
