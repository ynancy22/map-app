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
    """
    加載字體邏輯：優先使用本地 Iansui (汧水體) 以支援中文。
    """
    iansui_path = os.path.join(FONTS_DIR, "Iansui-Regular.ttf")

    # 1. 嘗試註冊本地汧水體
    if os.path.exists(iansui_path):
        try:
            fm.fontManager.addfont(iansui_path)
            return {
                "bold": iansui_path,
                "regular": iansui_path,
                "light": iansui_path,
            }
        except Exception:
            pass

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

FONTS = load_fonts()
THEME = {} 

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

def create_poster(city, country, point, dist, output_file, output_format, width=12, height=16, fonts=None, city_scale=1.0, country_scale=1.0, line_scale=1.0, custom_text=None, custom_text_size=18):
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
    active_fonts = fonts or FONTS

    # 城市名 (支援中文)
    f_main = FontProperties(fname=active_fonts["bold"], size=60 * city_scale * sf)
    display_city = "  ".join(list(city.upper())) if is_latin_script(city) else city
    ax.text(0.5, 0.14, display_city, transform=ax.transAxes, color=THEME["text"], ha="center", fontproperties=f_main, zorder=11)

    # 國家與座標
    f_sub = FontProperties(fname=active_fonts["light"], size=22 * country_scale * sf)
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes, color=THEME["text"], ha="center", fontproperties=f_sub, zorder=11)
    
    f_coords = FontProperties(fname=active_fonts["regular"], size=14 * sf)
    coord_text = f"{abs(point[0]):.4f}° {'N' if point[0]>=0 else 'S'} / {abs(point[1]):.4f}° {'E' if point[1]>=0 else 'W'}"
    ax.text(0.5, 0.07, coord_text, transform=ax.transAxes, color=THEME["text"], alpha=0.7, ha="center", fontproperties=f_coords, zorder=11)

    if custom_text:
        f_cust = FontProperties(fname=active_fonts["light"], size=custom_text_size * sf)
        ax.text(0.5, 0.04, custom_text, transform=ax.transAxes, color=THEME["text"], alpha=0.8, ha="center", fontproperties=f_cust, zorder=11)

    plt.savefig(output_file, facecolor=THEME["bg"], bbox_inches="tight", pad_inches=0.05, dpi=300)
    plt.close()

# --- 6. CLI 介面 (保持您的 argparse 邏輯) ---
if __name__ == "__main__":
    # (此處可保留您原本的 argparse 邏輯，或視需求簡化)
    pass
