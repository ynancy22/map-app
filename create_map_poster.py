#!/usr/bin/env python3
"""
City Map Poster Generator

This module generates beautiful, minimalist map posters for any city in the world.
It fetches OpenStreetMap data using OSMnx, applies customizable themes, and creates
high-quality poster-ready images with roads, water features, and parks.
"""

import argparse
import asyncio
import json
import os
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import cast, Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import osmnx as ox
from geopandas import GeoDataFrame
from geopy.geocoders import Nominatim
from lat_lon_parser import parse
from matplotlib.font_manager import FontProperties
from networkx import MultiDiGraph
from shapely.geometry import Point
from tqdm import tqdm

# 嘗試從本地模組匯入，若失敗則使用內建邏輯
try:
    from font_management import load_fonts as external_load_fonts
except ImportError:
    external_load_fonts = None

class CacheError(Exception):
    """Raised when a cache operation fails."""

# --- 1. 基礎配置與路徑 (整合環境變數) ---
CACHE_DIR_PATH = os.environ.get("CACHE_DIR", "cache")
CACHE_DIR = Path(CACHE_DIR_PATH)
CACHE_DIR.mkdir(exist_ok=True)

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"
FILE_ENCODING = "utf-8"


# FONTS = load_fonts()
THEME = {} 


# --- 2. 緩存工具函數 (修正 _cache_path 未定義問題) ---
def _cache_path(key: str) -> Path:
    """產生安全且唯一的緩存檔案路徑"""
    safe = str(key).replace(os.sep, "_").replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe}.pkl"

def cache_get(key: str):
    """Retrieve a cached object by key."""
    try:
        path = _cache_path(key)
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        # 不拋出錯誤，僅回傳 None 讓程式重新抓取數據
        print(f"Cache read info: {e}")
        return None

def cache_set(key: str, value):
    """Store an object in the cache."""
    try:
        path = _cache_path(key)
        with open(path, "wb") as f:
            pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as e:
        print(f"Cache write failed: {e}")

# --- 3. 字體加載邏輯 (汧水體偵測與回退) ---
def load_fonts(font_family: Optional[str] = None) -> dict:

    # 2. 如果指定了 Google Fonts 則嘗試透過外部模組載入
    if font_family and external_load_fonts:
        res = external_load_fonts(font_family)
        if res: return res

    # 3. 最終回退到 Roboto
    return {
        "bold": os.path.join(FONTS_DIR, "Roboto-Bold.ttf"),
        "regular": os.path.join(FONTS_DIR, "Roboto-Regular.ttf"),
        "light": os.path.join(FONTS_DIR, "Roboto-Light.ttf"),
    }



# --- 4. 功能性工具函數 ---

def is_latin_script(text):
    """Check if text is primarily Latin script for letter-spacing."""
    if not text: return True
    latin_count = sum(1 for char in text if char.isalpha() and ord(char) < 0x250)
    total_alpha = sum(1 for char in text if char.isalpha())
    if total_alpha == 0: return True
    return (latin_count / total_alpha) > 0.8

def generate_output_filename(city, theme_name, output_format):
    """Generate unique output filename."""
    Path(POSTERS_DIR).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(" ", "_")
    return os.path.join(POSTERS_DIR, f"{city_slug}_{theme_name}_{timestamp}.{output_format}")

def get_available_themes():
    """List available themes."""
    if not os.path.exists(THEMES_DIR): return []
    return [f[:-5] for f in sorted(os.listdir(THEMES_DIR)) if f.endswith(".json")]

def load_theme(theme_name="terracotta"):
    """Load theme from JSON."""
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    if not os.path.exists(theme_file):
        return {
            "name": "Terracotta", "bg": "#F5EDE4", "text": "#8B4513",
            "gradient_color": "#F5EDE4", "water": "#A8C4C4", "parks": "#E8E0D0",
            "road_motorway": "#A0522D", "road_primary": "#B8653A", "road_secondary": "#C9846A",
            "road_tertiary": "#D9A08A", "road_residential": "#E5C4B0", "road_default": "#D9A08A",
        }
    with open(theme_file, "r", encoding=FILE_ENCODING) as f:
        return json.load(f)

# --- 5. 繪圖核心函數 ---

def setup_global_fonts():
    """
    註冊所有 Roboto 與 Noto Sans TC 字種，並設定全域字體回退機制。
    """
    fonts_dir = "fonts"
    # 修正 1：補上 NotoSansTC-Light.ttf 後方遺失的逗號
    font_files = [
        "Roboto-Regular.ttf", "Roboto-Bold.ttf", "Roboto-Light.ttf",
        "NotoSansTC-Regular.ttf", "NotoSansTC-Bold.ttf", "NotoSansTC-Light.ttf",
        "NotoColorEmoji-Regular.ttf"
    ]

    for f in font_files:
        path = os.path.join(fonts_dir, f)
        if os.path.exists(path):
            try:
                fm.fontManager.addfont(path)
            except Exception as e:
                print(f"字體註冊警告 {f}: {e}")
    
    # 修正 2：在 print 之前先定義 registered_emoji 變數
    # 這樣能動態偵測 Linux 系統中的 Emoji 家族名稱 (通常為 'Noto Color Emoji')
    registered_emoji = [f.name for f in fm.fontManager.ttflist if 'Emoji' in f.name]
    emoji_family = registered_emoji[0] if registered_emoji else 'Noto Color Emoji'

    # 設定全域字體回退清單
    plt.rcParams['font.sans-serif'] = ['Roboto', 'Noto Sans TC', 'Noto Color Emoji', 'DejaVu Sans', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False 

    # 現在可以安全地印出診斷資訊，不會再報 NameError
    print(f"DEBUG: 成功註冊的 Emoji 字體: {registered_emoji}")

# 執行全域設定
setup_global_fonts()



def create_gradient_fade(ax, color, location="bottom", zorder=10):
    """Creates a fade effect at the top or bottom."""
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, :3] = rgb
    if location == "bottom":
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent = [ax.get_xlim()[0], ax.get_xlim()[1], ax.get_ylim()[0], ax.get_ylim()[0] + (ax.get_ylim()[1]-ax.get_ylim()[0])*0.25]
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent = [ax.get_xlim()[0], ax.get_xlim()[1], ax.get_ylim()[1] - (ax.get_ylim()[1]-ax.get_ylim()[0])*0.25, ax.get_ylim()[1]]
    
    ax.imshow(gradient, extent=extent, aspect="auto", cmap=mcolors.ListedColormap(my_colors), zorder=zorder, origin="lower")

def get_edge_colors_by_type(g):
    edge_colors = []
    for u, v, data in g.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list): highway = highway[0]
        if highway in ["motorway", "motorway_link"]: color = THEME["road_motorway"]
        elif highway in ["trunk", "trunk_link", "primary", "primary_link"]: color = THEME["road_primary"]
        elif highway in ["secondary", "secondary_link"]: color = THEME["road_secondary"]
        elif highway in ["tertiary", "tertiary_link"]: color = THEME["road_tertiary"]
        else: color = THEME.get("road_residential", THEME["road_default"])
        edge_colors.append(color)
    return edge_colors

def get_edge_widths_by_type(g):
    edge_widths = []
    for u, v, data in g.edges(data=True):
        highway = data.get('highway', 'unclassified')
        if isinstance(highway, list): highway = highway[0]
        if highway in ["motorway", "motorway_link"]: width = 1.2
        elif highway in ["trunk", "trunk_link", "primary", "primary_link"]: width = 1.0
        elif highway in ["secondary", "secondary_link"]: width = 0.8
        else: width = 0.4
        edge_widths.append(width)
    return edge_widths

def get_coordinates(city, country):
    key = f"coords_{city.lower()}_{country.lower()}"
    cached = cache_get(key)
    if cached: return cached

    # 使用更像瀏覽器的 User-Agent，並加入 timeout
    geolocator = Nominatim(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) MapApp/1.0", 
        timeout=10
    )
    # 嘗試最多 3 次，每次失敗後停頓 2 秒
    for attempt in range(3):
        try:
            location = geolocator.geocode(f"{city}, {country}")
            if location:
                coords = (location.latitude, location.longitude)
                cache_set(key, coords)
                return coords
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise ValueError(f"地理編碼服務暫時不可用 (嘗試 3 次皆失敗): {e}")
    
    raise ValueError(f"找不到城市: {city}, {country}")

    geolocator = Nominatim(user_agent="city_map_poster", timeout=10)
    time.sleep(1)
    location = geolocator.geocode(f"{city}, {country}")
    if location:
        coords = (location.latitude, location.longitude)
        cache_set(key, coords)
        return coords
    raise ValueError(f"Could not find coordinates for {city}")

def get_crop_limits(g_proj, center_lat_lon, fig, dist):
    lat, lon = center_lat_lon
    center = ox.projection.project_geometry(Point(lon, lat), crs="EPSG:4326", to_crs=g_proj.graph["crs"])[0]
    aspect = fig.get_size_inches()[0] / fig.get_size_inches()[1]
    hx, hy = (dist, dist/aspect) if aspect > 1 else (dist*aspect, dist)
    return ((center.x - hx, center.x + hx), (center.y - hy, center.y + hy))

def fetch_graph(point, dist) -> MultiDiGraph:
    key = f"graph_{point[0]}_{point[1]}_{dist}"
    cached = cache_get(key)
    if cached: return cast(MultiDiGraph, cached)
    g = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all', truncate_by_edge=True)
    cache_set(key, g)
    return g

def fetch_features(point, dist, tags, name) -> GeoDataFrame:
    key = f"{name}_{point[0]}_{point[1]}_{dist}"
    cached = cache_get(key)
    if cached: return cast(GeoDataFrame, cached)
    data = ox.features_from_point(point, tags=tags, dist=dist)
    cache_set(key, data)
    return data

def create_poster(city, country, point, dist, output_file, output_format, width=12, height=16, fonts=None, city_scale=1.0, country_scale=1.0, line_scale=1.0, custom_text=None, custom_text_size=18, show_coords=True):
    # 下載數據
    comp_dist = dist * (max(height, width) / min(height, width)) / 4
    g = fetch_graph(point, comp_dist)
    water = fetch_features(point, comp_dist, {"natural": ["water", "bay"], "waterway": "riverbank"}, "water")
    parks = fetch_features(point, comp_dist, {"leisure": "park", "landuse": "grass"}, "parks")

    # 設定畫布
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME["bg"])
    ax.set_position((0, 0, 1, 1))
    g_proj = ox.project_graph(g)

    # 繪製
    # 使用 is not None 確保物件存在，使用 not water.empty 確保裡面有資料
    if water is not None and not water.empty:
        water.to_crs(g_proj.graph['crs']).plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=0.5)

    if parks is not None and not parks.empty:
        parks.to_crs(g_proj.graph['crs']).plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=0.8)
        
    widths = [w * line_scale for w in get_edge_widths_by_type(g_proj)]
    ox.plot_graph(g_proj, ax=ax, bgcolor=THEME['bg'], node_size=0, edge_color=get_edge_colors_by_type(g_proj), edge_linewidth=widths, show=False, close=False)
    
    xlim, ylim = get_crop_limits(g_proj, point, fig, comp_dist)
    ax.set_xlim(xlim); ax.set_ylim(ylim)

    # 裝飾與文字
    create_gradient_fade(ax, THEME['gradient_color'], 'bottom'); create_gradient_fade(ax, THEME['gradient_color'], 'top')
    sf = min(height, width) / 12.0
    # 統一使用的字體家族清單
    target_family = ['Roboto', 'Noto Sans TC', 'Noto Color Emoji']
    # target_family = 'sans-serif'
    # 1. 繪製城市 (City) - 使用 Bold
    display_city = "  ".join(list(city.upper())) if is_latin_script(city) else city
    ax.text(0.5, 0.14, display_city, transform=ax.transAxes, color=THEME["text"], 
            ha="center", fontsize=60 * city_scale * sf, weight='bold', zorder=11)

    # 2. 繪製國家 (Country) - 使用 Light
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes, color=THEME["text"], 
            ha="center", fontsize=22 * country_scale * sf, weight='light', zorder=11)

    coord_y = 0.07  # 座標的預設高度
    
    # 繪製座標 (僅在勾選時顯示)
    if show_coords:
        lat, lon = point
        coord_text = f"{abs(lat):.4f}° {'N' if lat>=0 else 'S'} / {abs(lon):.4f}° {'E' if lon>=0 else 'W'}"
        ax.text(0.5, 0.07, coord_text, transform=ax.transAxes, color=THEME["text"], 
                alpha=0.7, ha="center", fontsize=14 * sf, zorder=11)        
        # 如果有顯示座標，客製化文字放在比較低的位置
        custom_y = 0.04
    else:
        # 如果隱藏座標，客製化文字往上移動到接近原本座標的位置
        custom_y = 0.06
   

    if custom_text:
        ax.text(0.5, custom_y, custom_text, transform=ax.transAxes, color=THEME["text"], 
                alpha=0.8, ha="center", fontsize=custom_text_size * sf, zorder=11)
    plt.savefig(output_file, facecolor=THEME["bg"], bbox_inches="tight", pad_inches=0.05, dpi=300)
    plt.close()

# --- 6. CLI 介面 (保持您的 argparse 邏輯) ---
if __name__ == "__main__":
    # (此處可保留您原本的 argparse 邏輯，或視需求簡化)
    pass
