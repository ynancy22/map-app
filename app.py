import streamlit as st
import os
from create_map_poster import create_poster, load_theme

# 網頁標題
st.set_page_config(page_title="MapToPoster Web", page_icon="📍")
st.title("📍 MapToPoster 網頁版")
st.write("輸入城市與國家，生成專屬的極簡風格地圖海報。")

# 側邊欄設定
with st.sidebar:
    st.header("設定參數")
    city = st.text_input("城市名稱 (City)", "Taipei")
    country = st.text_input("國家名稱 (Country)", "Taiwan")
    
    # 取得所有主題
    theme_folder = 'themes'
    available_themes = [f.replace('.json', '') for f in os.listdir(theme_folder) if f.endswith('.json')]
    selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=available_themes.index('terracotta') if 'terracotta' in available_themes else 0)
    
    distance = st.slider("地圖半徑 (Meters)", 2000, 20000, 10000)
    
# 生成按鈕
if st.button("開始生成海報"):
    with st.spinner("正在抓取地圖數據並繪圖，請稍候..."):
        try:
            # 呼叫原始專案的函數
            theme_config = load_theme(selected_theme)
            
            # 建立暫存路徑
            if not os.path.exists("posters"):
                os.makedirs("posters")
            
            # 這裡調用原本腳本的核心邏輯 (請確保 create_map_poster.py 的函數可被導入)
            # 提示：你可能需要微調原作者的 create_poster 函數，確保它能回傳圖片物件或存檔路徑
            output_file = f"posters/{city}_{selected_theme}.png"
            
            # 執行生成 (參考原作者 create_map_poster.py 內容)
            create_poster(city, country, selected_theme, distance, output_file)
            
            # 顯示圖片
            st.image(output_file, caption=f"{city}, {country} - {selected_theme}")
            
            # 下載按鈕
            with open(output_file, "rb") as file:
                st.download_button(
                    label="下載高解析度海報",
                    data=file,
                    file_name=f"{city}_poster.png",
                    mime="image/png"
                )
        except Exception as e:
            st.error(f"生成失敗: {e}")
