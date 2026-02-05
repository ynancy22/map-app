"""
Font Management Module
Handles font loading, Google Fonts integration, and caching.
"""

import os
import re
from pathlib import Path
from typing import Optional

import requests
import matplotlib.font_manager as fm
from fontTools.ttLib import TTFont  # 需要在 requirements.txt 加入 fonttools

FONTS_DIR = "fonts"
FONTS_CACHE_DIR = Path(FONTS_DIR) / "cache"


def download_google_font(font_family: str, weights: list = None) -> Optional[dict]:
    """
    Download a font family from Google Fonts and cache it locally.
    Returns dict with font paths for different weights, or None if download fails.

    :param font_family: Google Fonts family name (e.g., 'Noto Sans JP', 'Open Sans')
    :param weights: List of font weights to download (300=light, 400=regular, 700=bold)
    :return: Dict with 'light', 'regular', 'bold' keys mapping to font file paths
    """
    if weights is None:
        weights = [300, 400, 700]

    # Create fonts cache directory
    FONTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Normalize font family name for file paths
    font_name_safe = font_family.replace(" ", "_").lower()

    font_files = {}

    try:
        # Google Fonts API endpoint - request all weights at once
        weights_str = ";".join(map(str, weights))
        api_url = "https://fonts.googleapis.com/css2"

        # Use requests library for cleaner HTTP handling
        params = {"family": f"{font_family}:wght@{weights_str}"}
        headers = {
            "User-Agent": "Mozilla/5.0"  # Get .woff2 files (better compression)
        }

        # Fetch CSS file
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        css_content = response.text

        # Parse CSS to extract weight-specific URLs
        # Google Fonts CSS has @font-face blocks with font-weight and src: url()
        weight_url_map = {}

        # Split CSS into font-face blocks
        font_face_blocks = re.split(r"@font-face\s*\{", css_content)

        for block in font_face_blocks[1:]:  # Skip first empty split
            # Extract font-weight
            weight_match = re.search(r"font-weight:\s*(\d+)", block)
            if not weight_match:
                continue

            weight = int(weight_match.group(1))

            # Extract URL (prefer woff2, fallback to ttf)
            url_match = re.search(r"url\((https://[^)]+\.(woff2|ttf))\)", block)
            if url_match:
                weight_url_map[weight] = url_match.group(1)

        # Map weights to our keys
        weight_map = {300: "light", 400: "regular", 700: "bold"}

        # Download each weight
        for weight in weights:
            weight_key = weight_map.get(weight, "regular")

            # Find URL for this weight
            weight_url = weight_url_map.get(weight)

            # If exact weight not found, try to find closest
            if not weight_url and weight_url_map:
                # Find closest weight
                closest_weight = min(
                    weight_url_map.keys(), key=lambda x: abs(x - weight)
                )
                weight_url = weight_url_map[closest_weight]
                print(
                    f"  Using weight {closest_weight} for {weight_key} (requested {weight} not available)"
                )

            if weight_url:
                # Determine file extension
                file_ext = "woff2" if weight_url.endswith(".woff2") else "ttf"

                # Download font file
                font_filename = f"{font_name_safe}_{weight_key}.{file_ext}"
                font_path = FONTS_CACHE_DIR / font_filename

                if not font_path.exists():
                    print(f"  Downloading {font_family} {weight_key} ({weight})...")
                    try:
                        font_response = requests.get(weight_url, timeout=10)
                        font_response.raise_for_status()
                        font_path.write_bytes(font_response.content)
                    except Exception as e:
                        print(f"  ⚠ Failed to download {weight_key}: {e}")
                        continue
                else:
                    print(f"  Using cached {font_family} {weight_key}")

                font_files[weight_key] = str(font_path)

        # Ensure we have at least regular weight
        if "regular" not in font_files and font_files:
            # Use first available as regular
            font_files["regular"] = list(font_files.values())[0]
            print(f"  Using {list(font_files.keys())[0]} weight as regular")

        # If we don't have all three weights, duplicate available ones
        if "bold" not in font_files and "regular" in font_files:
            font_files["bold"] = font_files["regular"]
            print("  Using regular weight as bold")
        if "light" not in font_files and "regular" in font_files:
            font_files["light"] = font_files["regular"]
            print("  Using regular weight as light")

        return font_files if font_files else None

    except Exception as e:
        print(f"⚠ Error downloading Google Font '{font_family}': {e}")
        return None


def load_fonts(font_family=None):
    """
    加載字體：優先偵測本地 Iansui-Regular.ttf。
    """
    # 獲取專案根目錄，確保在雲端環境路徑解析正確
    base_dir = Path(__file__).parent
    # 強制轉換為字串路徑，避免 Python 3.13 的相容性問題
    iansui_path = str(base_dir / "fonts" / "Iansui-Regular.ttf")

    if os.path.exists(iansui_path):
        try:
            # 嘗試註冊字體到 Matplotlib
            fm.fontManager.addfont(iansui_path)
            print(f"✓ 成功註冊字體: {iansui_path}")
            return {
                "bold": iansui_path,
                "regular": iansui_path,
                "light": iansui_path
            }
        except Exception as e:
            # 如果檔案損壞 (FT2Font error) 會跳到這裡
            print(f"⚠ 字體檔案無法讀取 (損壞或格式錯誤): {e}")
    
    # 安全回退機制：改用 Roboto 或系統字體
    print("正在回退至預設 Roboto 字體...")
    return {
        "bold": str(base_dir / "fonts" / "Roboto-Bold.ttf"),
        "regular": str(base_dir / "fonts" / "Roboto-Regular.ttf"),
        "light": str(base_dir / "fonts" / "Roboto-Light.ttf")
    }

def has_glyph(font_path, char):
    """偵測字體是否包含特定字元"""
    font = TTFont(font_path)
    for table in font['cmap'].tables:
        if ord(char) in table.cmap:
            return True
    return False

def render_mixed_text(ax, x, y, text, fontsize, color, **kwargs):
    """
    自動偵測 Emoji 並嘗試使用特定字體渲染。
    Matplotlib 原生對彩色 Emoji 支援有限，此處建議使用支援 Emoji 的字體。
    """
    emoji_font_path = "fonts/NotoColorEmoji.ttf"
    standard_fonts = ['Roboto', 'Noto Sans TC', 'sans-serif']
    
    # 這裡使用簡單的區塊渲染或設定回退鏈
    # 注意：Matplotlib 3.4+ 支援部分彩色字體渲染
    if os.path.exists(emoji_font_path):
        # 將 Emoji 字體加入回退鏈的最前端（或根據需求調整）
        combined_families = standard_fonts + ['Noto Color Emoji']
        fm.fontManager.addfont(emoji_font_path)
    else:
        combined_families = standard_fonts

    return ax.text(x, y, text, transform=ax.transAxes, 
                   fontfamily=combined_families, 
                   fontsize=fontsize, color=color, 
                   ha="center", va="center", **kwargs)
