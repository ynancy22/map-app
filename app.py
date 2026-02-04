import streamlit as st
import os
# 從你上傳的檔案中匯入核心功能
from create_map_poster import create_poster, load_theme, get_coordinates

# 網頁標題
st.set_page_config(page_title="MapToPoster Web", page_icon="📍")
st.title("📍 MapToPoster 網頁版")
st.write("輸入城市與國家，生成專屬的極簡風格地圖海報。")

# 側邊欄設定
with st.sidebar:
    st.header("設定參數")
    city = st.text_input("城市名稱 (City)", "Taipei")
    country = st.text_input("國家名稱 (Country)", "Taiwan")
    
    # 取得所有主題 (確保 themes/ 資料夾內有 .json 檔案)
    theme_folder = 'themes'
    if os.path.exists(theme_folder):
        available_themes = [f.replace('.json', '') for f in os.listdir(theme_folder) if f.endswith('.json')]
    else:
        available_themes = ["terracotta"] # 備用選項
        
    selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=0)
    distance = st.slider("地圖半徑 (Meters)", 2000, 20000, 10000)

# 生成按鈕
if st.button("開始生成海報"):
    with st.spinner("正在抓取地圖數據並繪圖，這可能需要一分鐘，請稍候..."):
        try:
            # 1. 取得座標
            coords = get_coordinates(city, country)
            
            # 2. 載入主題配置
            # 注意：這裡必須更新全域變數 THEME，因為原腳本繪圖時會參考它
            import create_map_poster
            create_map_poster.THEME = load_theme(selected_theme)
            
            # 3. 建立儲存目錄
            if not os.path.exists("posters"):
                os.makedirs("posters")
            output_file = f"posters/{city}_{selected_theme}.png"
            
            # 4. 呼叫原始生成函數 (修正參數名稱以符合原代碼第 455 行)
            create_poster(
                city=city,
                country=country,
                point=coords,        # 原代碼使用 point 作為參數名
                dist=distance,
                output_file=output_file,
                output_format="png"  # 原代碼要求指定格式
            )
            
            # 5. 顯示圖片
            st.image(output_file, caption=f"{city}, {country} - {selected_theme}")
            
            # 6. 下載按鈕
            with open(output_file, "rb") as file:
                st.download_button(
                    label="下載高解析度海報",
                    data=file,
                    file_name=f"{city}_poster.png",
                    mime="image/png"
                )
        except Exception as e:
            st.error(f"生成失敗: {e}")
            st.info("請檢查 'themes/' 資料夾中是否包含主題檔案，以及網路連線是否正常。")
