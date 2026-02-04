def create_poster(
    city,
    country,
    point,
    dist,
    output_file,
    output_format,
    width=12,
    height=16,
    country_label=None,
    name_label=None,
    display_city=None,
    display_country=None,
    fonts=None,
    city_scale=1.0,      # 接收城市文字大小縮放
    country_scale=1.0,   # 接收國家文字大小縮放
    line_scale=1.0,      # 接收線條粗細縮放
    custom_text=None,    # 接收客製化紀念文字
    custom_text_size=18  # 接收客製化文字大小
):
    display_city = display_city or name_label or city
    display_country = display_country or country_label or country

    # 1. 抓取數據
    compensated_dist = dist * (max(height, width) / min(height, width)) / 4
    g = fetch_graph(point, compensated_dist)
    if g is None:
        raise RuntimeError("無法獲取地圖數據，請檢查城市名稱或網路。")

    water = fetch_features(point, compensated_dist, tags={"natural": ["water", "bay", "strait"], "waterway": "riverbank"}, name="water")
    parks = fetch_features(point, compensated_dist, tags={"leisure": "park", "landuse": "grass"}, name="parks")

    # 2. 設定畫布
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    ax.set_position((0.0, 0.0, 1.0, 1.0))
    g_proj = ox.project_graph(g)

    # 3. 繪製圖層
    if water is not None and not water.empty:
        water.to_crs(g_proj.graph['crs']).plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=0.5)
    if parks is not None and not parks.empty:
        parks.to_crs(g_proj.graph['crs']).plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=0.8)

    # 4. 繪製道路 (套用 line_scale)
    edge_colors = get_edge_colors_by_type(g_proj)
    edge_widths = [w * line_scale for w in get_edge_widths_by_type(g_proj)]

    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)
    ox.plot_graph(g_proj, ax=ax, bgcolor=THEME['bg'], node_size=0, edge_color=edge_colors, edge_linewidth=edge_widths, show=False, close=False)
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)

    # 5. 漸層與文字 (套用 city_scale / country_scale)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)

    scale_factor = min(height, width) / 12.0
    active_fonts = fonts or FONTS

    # 繪製城市
    font_main = FontProperties(fname=active_fonts["bold"] if active_fonts else None, size=60 * city_scale * scale_factor)
    spaced_city = "  ".join(list(display_city.upper())) if is_latin_script(display_city) else display_city
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes, color=THEME["text"], ha="center", fontproperties=font_main, zorder=11)

    # 裝飾線
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, color=THEME["text"], linewidth=1 * scale_factor, zorder=11)

    # 國家
    font_sub = FontProperties(fname=active_fonts["light"] if active_fonts else None, size=22 * country_scale * scale_factor)
    ax.text(0.5, 0.10, display_country.upper(), transform=ax.transAxes, color=THEME["text"], ha="center", fontproperties=font_sub, zorder=11)

    # 座標
    lat, lon = point
    coord_text = f"{abs(lat):.4f}° {'N' if lat>=0 else 'S'} / {abs(lon):.4f}° {'E' if lon>=0 else 'W'}"
    font_coords = FontProperties(fname=active_fonts["regular"] if active_fonts else None, size=14 * scale_factor)
    ax.text(0.5, 0.07, coord_text, transform=ax.transAxes, color=THEME["text"], alpha=0.7, ha="center", fontproperties=font_coords, zorder=11)

    # --- 新增：客製化紀念文字 (繪製在座標下方) ---
    if custom_text:
        font_custom = FontProperties(fname=active_fonts["light"] if active_fonts else None, size=custom_text_size * scale_factor)
        ax.text(0.5, 0.04, custom_text, transform=ax.transAxes, color=THEME["text"], alpha=0.8, ha="center", fontproperties=font_custom, zorder=11)

    # 6. 儲存
    plt.savefig(output_file, facecolor=THEME["bg"], bbox_inches="tight", pad_inches=0.05, dpi=300)
    plt.close()
