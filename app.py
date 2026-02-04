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
    
    # --- 新增客製化文字欄位 ---
    custom_text = st.text_input("紀念文字 (選填)", placeholder="例如：Our First Date / 2026.02.14")
    custom_text_size = st.slider("紀念文字大小", 10, 30, 18)
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



# --- 初始化 Session State ---
# 用來儲存生成的圖片路徑，確保下載後不會消失
if 'poster_path' not in st.session_state:
    st.session_state.poster_path = None

# --- 生成按鈕 ---
if st.button("開始生成海報"):
    with st.spinner("正在處理數據並繪圖，請稍候..."):
        try:
            coords = get_coordinates(city, country)
            create_map_poster.THEME = load_theme(selected_theme)
            
            if not os.path.exists("posters"):
                os.makedirs("posters")
            
            output_file = f"posters/{city}_{selected_theme}.png"
            
            # 呼叫引擎
            # --- app.py 呼叫部分 ---
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
                custom_text=custom_text,      # 傳入客製化文字
                custom_text_size=custom_text_size # 傳入滑桿設定的大小
            )
            
            # 將結果存入 session_state
            st.session_state.poster_path = output_file
                
        except Exception as e:
            st.error(f"生成失敗: {e}")

# --- 顯示與下載區塊 (放在按鈕外) ---
# 只要 session_state 裡面有路徑，就一直顯示
if st.session_state.poster_path and os.path.exists(st.session_state.poster_path):
    st.divider()
    st.image(st.session_state.poster_path, caption=f"預覽：{city}")
    
    with open(st.session_state.poster_path, "rb") as file:
        st.download_button(
            label="下載高解析度海報",
            data=file,
            file_name=f"{city}_poster.png",
            mime="image/png"
        )
