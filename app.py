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
    st.header("🎨 海報自訂選項")
    city = st.text_input("城市名稱 (City)", "Taipei")
    # 文字大小：城市
    city_size_opt = st.selectbox("城市文字大小", ["小", "中", "大"], index=1)
    
    country = st.text_input("國家名稱 (Country)", "Taiwan")
    # 文字大小：國家
    country_size_opt = st.selectbox("國家文字大小", ["小", "中", "大"], index=1)

    st.divider()

    # 地圖半徑：結合拉桿與輸入框
    st.write("地圖半徑 (Meters)")
    distance = st.number_input("直接輸入數值", value=10000, step=500)
    distance = st.select_slider(
        "或是選擇定點",
        options=[2000, 5000, 10000, 15000, 20000],
        value=distance if distance in [2000, 5000, 10000, 15000, 20000] else 10000
    )

    # 線條粗細
    line_width_opt = st.select_slider("線條粗細", options=["細", "標準", "粗"], value="標準")

    # 轉換選單數值為比例係數
    size_map = {"小": 0.7, "中": 1.0, "大": 1.4}
    line_map = {"細": 0.6, "標準": 1.0, "粗": 1.6}
    
    c_scale = size_map[city_size_opt]
    n_scale = size_map[country_size_opt]
    l_scale = line_map[line_width_opt]

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
            # 呼叫修正後的引擎
            create_poster(
                city=city,
                country=country,
                point=coords,
                dist=distance,
                output_file=output_file,
                output_format="png",
                city_scale=c_scale,      # 傳入城市文字縮放
                country_scale=n_scale,   # 傳入國家文字縮放
                line_scale=l_scale       # 傳入線條縮放
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
