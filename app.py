import streamlit as st
import os
import shutil
from pathlib import Path
import create_map_poster
from create_map_poster import create_poster, load_theme, get_coordinates
import os
from pathlib import Path
import osmnx as ox
import matplotlib.font_manager as fm

# 強制定義快取位置
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 徹底設定 ox 的路徑，避免它亂跑
ox.settings.cache_folder = str(CACHE_DIR.absolute())
ox.settings.use_cache = True
ox.settings.log_console = False  # 關閉日誌寫入檔案，這常引起權限錯誤

# 網頁配置
st.set_page_config(page_title="MapToPoster", page_icon="📍")
st.title("📍 MapToPoster")
st.write("網頁版地圖生成器")
st.write("輸入城市與國家，生成專屬的極簡風格地圖海報。")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🎨 海報自訂選項 Options")
    
    city = st.text_input("城市 (City)", "Taipei")
    city_size_opt = st.radio("城市文字大小 font size", ["小 S", "中 M", "大 L"], index=1, horizontal=True)
    
    country = st.text_input("國家 (Country)", "Taiwan")
    country_size_opt = st.radio("國家文字大小 font size", ["小 S", "中 M", "大 L"], index=1, horizontal=True)
    
    # 客製化紀念文字
    custom_text = st.text_input("紀念文字 (選填) Customized text (optional)", placeholder="例如：Our First Date / 2019.02.14")
    custom_text_size = st.slider("紀念文字大小 font size", 10, 40, 18)

    # 座標顯示開關
    use_manual = st.toggle("手動輸入座標 (Manual input)", value=False)
    show_coords = st.toggle("顯示經緯度 (Show coordinates)", value=True)
   
    if use_manual:
        st.caption("在 Google Maps 欲製作的地點按右鍵即可複製座標")
        manual_lat = st.number_input("緯度 Lat", value=0, format="%.4f")
        manual_lon = st.number_input("經度 Lon", value=0, format="%.4f")
        coords = (manual_lat, manual_lon)
    else:
        coords = None # 由 get_coordinates 自動獲取
    st.divider()

    # 地圖半徑控制
    st.write("地圖半徑 (Map range)")
    final_dist = st.select_slider(
        "選擇定點 Radius",
        options=[2000, 4000, 6000, 8000, 10000, 15000, 20000],
        value=10000,
        label_visibility="collapsed" 
    )

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
    
    #v selected_theme = st.selectbox("選擇主題 (Theme)", available_themes, index=0)



# 設定預覽圖目錄 (剛才生成的三色帶 PNG)
PREVIEW_DIR = Path("theme_previews")
def grid_theme_selector():
    st.sidebar.subheader("🎨 點擊方塊切換主題")
    
    # 核心 CSS：隱藏按鈕視覺，但保留點擊功能並覆蓋全區
    st.sidebar.markdown("""
        <style>
        /* 1. 定義容器與圖片樣式 */
        .theme-container {
            position: relative;
            width: 100%;
            cursor: pointer;
            margin-bottom: -30px; /* 關鍵：強制縮減 Streamlit 預設的按鈕間距 */
        }
        .theme-container img {
            width: 100%;
            border-radius: 8px;
            display: block;
            transition: transform 0.1s;
        }
        /* 2. 選中時的紅色外框 */
        .selected-tile img {
            outline: 3px solid #FF4B4B;
            outline-offset: 2px;
        }
        /* 3. 徹底隱藏下方的按鈕方框 */
        .theme-container div[data-testid="stButton"] {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        .theme-container button {
            width: 100% !important;
            height: 100% !important;
            background-color: transparent !important;
            border: none !important;
            color: transparent !important;
            padding: 0 !important;
            margin: 0 !important;
            /* 關鍵：讓按鈕完全透明但仍可點擊 */
            visibility: visible !important;
        }
        /* 移除點擊時的任何背景變色 */
        .theme-container button:hover, .theme-container button:active, .theme-container button:focus {
            background: transparent !important;
            box-shadow: none !important;
            color: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)

    theme_files = sorted(list(PREVIEW_DIR.glob("*.png")))
    if not theme_files:
        st.sidebar.warning("找不到預覽圖")
        return "default"

    if "selected_theme" not in st.session_state:
        st.session_state.selected_theme = theme_files[0].stem

    # 繪製網格
    cols_per_row = 6
    for i in range(0, len(theme_files), cols_per_row):
        cols = st.sidebar.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(theme_files):
                theme_path = theme_files[i + j]
                theme_name = theme_path.stem
                is_selected = st.session_state.selected_theme == theme_name
                
                with col:
                    # 使用 wrapper div 包裹
                    selected_class = "selected-tile" if is_selected else ""
                    st.markdown(f'<div class="theme-container {selected_class}">', unsafe_allow_html=True)
                    
                    # 顯示圖片
                    st.image(str(theme_path), use_container_width=True)
                    
                    # 放置透明按鈕，這會透過 CSS 覆蓋在圖片上並消除下方空間
                    if st.button("", key=f"t_{theme_name}"):
                        st.session_state.selected_theme = theme_name
                        st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)

    return st.session_state.selected_theme
# 在主程式中調用
# current_theme = grid_theme_selector()


def theme_selector_with_single_preview():
    # st.sidebar.subheader("🎨 地圖配色 Theme")
    
    # 1. 獲取所有主題清單 (從預覽圖資料夾抓取檔案名稱)
    theme_files = sorted([f.stem for f in PREVIEW_DIR.glob("*.png")])
    
    if not theme_files:
        st.sidebar.warning("找不到預覽圖，請先執行生成腳本")
        return "default"

    # 2. 原生下拉式文字清單
    # 如果先前有選過，則保留選擇狀態
    if "selected_theme" not in st.session_state:
        st.session_state.selected_theme = theme_files[0]

    selected_theme = st.sidebar.selectbox(
        "選擇主題配色 Select theme",
        theme_files,
        index=theme_files.index(st.session_state.selected_theme)
    )
    st.session_state.selected_theme = selected_theme

   # 3. 調整預覽配置：兩欄顯示
    # 左欄 1/3 寬度，右欄 2/3 寬度
    col1, col2 = st.sidebar.columns([1, 4])
    
    preview_path = PREVIEW_DIR / f"{selected_theme}.png"
    with col1:
        # 左側顯示預覽圖：更新為 width='stretch' 以符合 2026 版本規範
        if preview_path.exists():
            st.image(str(preview_path), width='stretch')
        else:
            st.write("🖼️")
            
    with col2:
        # 右側顯示相關文字
        # st.write(f"**{selected_theme}**")
        # 這裡可以根據主題名稱顯示描述，或是顯示色彩分析
        st.caption("(預覽：文字/背景/道路)")
        st.caption("(Preview: text/bg/road)")
    
    return selected_theme

# 在主程式中調用
selected_theme = theme_selector_with_single_preview()

# 轉換比例係數
size_map = {"小 S": 0.7, "中 M": 1.0, "大 L": 1.4}
line_map = {"細 Light": 0.6, "標準 Regular": 1.0, "粗 Bold": 1.6}

# 初始化 Session State
if 'poster_path' not in st.session_state:
    st.session_state.poster_path = None

# --- 主畫面按鈕與 Footer ---
st.divider()

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    generate_btn = st.button("GO!", use_container_width=True)

# Footer 標籤
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: rgba(0, 0, 0, 0.7); 
        color: gray;
        text-align: center;
        padding: 10px 0;
        font-size: 0.8em;
        z-index: 999;
    }
    .footer a {
        text-decoration: none;
    }
    .main .block-container {
        padding-bottom: 80px;
    }
    </style>
    <div class="footer">
        <span>Source:</span>
        <a href="https://github.com/originalankur/maptoposter" target="_blank">
            <img src="https://flat.badgen.net/badge/icon/github?icon=github&label=originalankur/maptoposter&color=black">
        </a>
        <span style="margin-left:15px;">Made by:</span>
        <a href="https://github.com/ynancy22/map-app" target="_blank">
            <img src="https://flat.badgen.net/badge/icon/github?icon=github&label=ynancy22/map-app&color=cyan">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)



# --- 生成邏輯 ---
if generate_btn:
    # 確保清理時目錄是存在的
    if CACHE_DIR.exists():
        with st.spinner("正在優化快取數據..."):
            for pkl in CACHE_DIR.glob("*.pkl"):
                # 保留座標快取，只刪除地圖圖資
                if any(prefix in pkl.name for prefix in ["graph_", "water_", "parks_"]):
                    try:
                        # 使用 os.chmod 確保檔案是可寫入狀態 (預防萬一)
                        os.chmod(pkl, 0o666) 
                        pkl.unlink()
                    except Exception as e:
                        # 即使刪除失敗也繼續執行，不要讓整個 App 崩潰
                        st.warning(f"暫時無法清理部分快取: {pkl.name}")

    with st.spinner("正在處理數據並繪圖，請稍候... Processing..."):
        try:
            # 獲取座標
            coords = get_coordinates(city, country)
            create_map_poster.THEME = load_theme(selected_theme)
            
            if not os.path.exists("posters"):
                os.makedirs("posters")
            
            output_file = f"posters/{city.replace(' ', '_')}_{selected_theme}.png"
            
            # 2. 呼叫核心引擎 (包含 show_coords 參數)
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
                custom_text_size=custom_text_size,
                show_coords=show_coords
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
