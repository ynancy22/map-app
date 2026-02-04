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

    st.divider()

    # 2. 地圖半徑控制 (結合輸入框與滑桿)
    st.write("地圖半徑 (Meters)")
    dist_input = st.number_input("直接輸入數值", value=10000, step=500)
    distance = st.select_slider(
        "或是選擇定點",
        options=[2000, 5000, 10000, 15000, 20000],
        value=dist_input if dist_input in [2000, 5000, 10000, 15000, 20000] else 10000
    )
    # 最終採用的距離以數值輸入框為準（若兩者衝突）
    final_dist = dist_input if dist_input != 10000 else distance

    # 3. 線條粗細
    line_width_opt = st.select_slider("線條粗細", options=["細", "標準", "粗"], value="標準")

    st.divider()

    # 4. 主題選擇 (修正變數未定義錯誤)
    theme_folder = 'themes'
    available_themes = []
    if os.path.exists(theme_folder):
        available_themes = [f.replace('.json', '') for f in os.listdir(theme_folder) if f.endswith('.json')]
    
    if not available_themes:
        available_themes = ["terracotta"] # 保險預設值
    
    # 確保變數名稱一致
    selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=0)

# --- 轉換選單數值為比例係數 ---
size_map = {"小": 0.7, "中": 1.0, "大": 1.4}
line_map = {"細": 0.6, "標準": 1.0, "粗": 1.6}

# --- 生成按鈕 ---
if st.button("開始生成海報"):
    with st.spinner("正在處理數據並繪圖，請稍候..."):
        try:
            # 1. 取得座標
            coords = get_coordinates(city, country)
            
            # 2. 設定主題全域變數
            create_map_poster.THEME = load_theme(selected_theme)
            
            # 3. 建立儲存目錄
            if not os.path.exists("posters"):
                os.makedirs("posters")
            output_file = f"posters/{city}_{selected_theme}.png"
            
            # 4. 呼叫引擎 (傳入新參數)
            create_poster(
                city=city,
                country=country,
                point=coords,
                dist=final_dist,
                output_file=output_file,
                output_format="png",
                city_scale=size_map[city_size_opt],
                country_scale=size_map[country_size_opt],
                line_scale=line_map[line_width_opt]
            )
            
            # 5. 顯示與下載
            st.image(output_file, caption=f"{city}, {country} - {selected_theme}")
            with open(output_file, "rb") as file:
                st.download_button("下載高解析度海報", data=file, file_name=f"{city}_poster.png", mime="image/png")
                
        except Exception as e:
            st.error(f"生成失敗: {e}")
