# 📍 MapToPoster (Customized Edition)

這是一個基於 Python 與 Streamlit 開發的極簡風格地圖海報生成器。使用者可以輸入全球任何城市，自訂主題、文字與排版，生成高品質的地圖藝術品。

---

## 🚀 快速開始 (Quick Start)

**此專案無需安裝，可直接透過瀏覽器使用：**
👉 **[MapToPoster 線上生成器](https://map-poster.streamlit.app/)**

---

## ✨ 核心功能 (Core Features)

* **智能字體替補 (Font Fallback)**: 
    * 英數字元優先使用 **Roboto**，展現現代設計感。
    * 中文字元（如台北、東京旅遊紀念文字）自動切換至 **Noto Sans TC**，徹底解決缺字方塊（豆腐字）問題。
* **動態排版優化**:
    * **座標開關**: 可自由選擇是否在海報上顯示地理座標。
    * **位置自動補償**: 當隱藏座標時，自訂紀念文字會自動上移（從 $y=0.04$ 移至 $y=0.06$），確保海報下方的視覺重心平衡。
* **連線備援系統**:
    * **手動座標模式**: 支援從 Google Maps 直接輸入座標，跳過地理編碼請求，解決伺服器連線被拒（Connection Refused）的問題。
    * **精確快取管理**: 點擊「GO!」時僅清理街道圖資快取，保留座標快取，避免重複請求導致的 API 封鎖。

---

## 🗺️ 使用說明 (Usage)

1.  **輸入地點**: 在側邊欄的「城市」與「國家」欄位輸入目標地點。
2.  **設定文字**: 在「紀念文字」欄位輸入您想顯示的語句（支援中英文混打）。
3.  **調整樣式**: 
    * 透過單選按鈕調整城市/國家文字的大小（S/M/L）。
    * 選擇色彩主題（如 Dark, Light, Blue 等）與街道線條粗細。
4.  **處理連線錯誤**: 
    * 若自動搜尋失敗（出現 Connection Refused），請開啟 **「啟用手動輸入座標」** 開關。
    * 在 Google Maps 對準地點按右鍵即可獲得緯度與經度，將其填入對應欄位。
5.  **生成與下載**: 點擊 **GO!** 後稍候片刻，預覽滿意即可點擊下載按鈕獲取 300 DPI 的高解析度 PNG 海報。


## 👤 作者與貢獻 (Credits)

Original Tool: 由 [originalankur/maptoposter](https://github.com/originalankur/maptoposter) 開發。
Customized & Maintained by: [ynancy22/map-app](https://github.com/ynancy22/map-app)

主要優化與功能開發：
   中英混合字體渲染引擎：開發了 Roboto 與 Noto Sans TC 的自動回退機制。
   座標自動排版位移：根據座標顯示狀態動態調整紀念文字位置，提升排版美感。
   手動座標輸入模式：有效解決 Nominatim API 請求次數限制的備援方案。
   精確快取管理系統：優化本地數據儲存邏輯以提升生成效率並防止網路封鎖。
