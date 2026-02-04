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
    # Corrected parameter definitions
    city_scale=1.0,
    country_scale=1.0,
    line_scale=1.0,
    custom_text=None,
    custom_text_size=18
):
    """
    Generate a complete map poster with roads, water, parks, and typography.
    """
    display_city = display_city or name_label or city
    display_country = display_country or country_label or country

    print(f"\nGenerating map for {city}, {country}...")

    # 1. Fetch Data
    with tqdm(total=3, desc="Fetching map data", unit="step") as pbar:
        compensated_dist = dist * (max(height, width) / min(height, width)) / 4
        g = fetch_graph(point, compensated_dist)
        if g is None:
            raise RuntimeError("Failed to retrieve street network data.")
        pbar.update(1)

        water = fetch_features(point, compensated_dist, 
                               tags={"natural": ["water", "bay", "strait"], "waterway": "riverbank"}, 
                               name="water")
        pbar.update(1)

        parks = fetch_features(point, compensated_dist, 
                               tags={"leisure": "park", "landuse": "grass"}, 
                               name="parks")
        pbar.update(1)

    # 2. Setup Plot
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME["bg"])
    ax.set_facecolor(THEME["bg"])
    ax.set_position((0.0, 0.0, 1.0, 1.0))

    g_proj = ox.project_graph(g)

    # 3. Plot Layers
    if water is not None and not water.empty:
        water_polys = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if not water_polys.empty:
            water_polys = water_polys.to_crs(g_proj.graph['crs'])
            water_polys.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=0.5)

    if parks is not None and not parks.empty:
        parks_polys = parks[parks.geometry.type.isin(["Polygon", "MultiPolygon"])]
        if not parks_polys.empty:
            parks_polys = parks_polys.to_crs(g_proj.graph['crs'])
            parks_polys.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=0.8)

    # Apply Line Scale
    edge_colors = get_edge_colors_by_type(g_proj)
    edge_widths = get_edge_widths_by_type(g_proj)
    edge_widths = [w * line_scale for w in edge_widths]

    crop_xlim, crop_ylim = get_crop_limits(g_proj, point, fig, compensated_dist)
    ox.plot_graph(g_proj, ax=ax, bgcolor=THEME['bg'], node_size=0,
                  edge_color=edge_colors, edge_linewidth=edge_widths,
                  show=False, close=False)
    
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)

    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)

    # 4. Typography
    scale_factor = min(height, width) / 12.0
    active_fonts = fonts or FONTS

    # Apply City and Country Scale
    base_main = 60 * city_scale * scale_factor
    base_sub = 22 * country_scale * scale_factor
    base_coords = 14 * scale_factor

    if active_fonts:
        font_main = FontProperties(fname=active_fonts["bold"], size=base_main)
        font_sub = FontProperties(fname=active_fonts["light"], size=base_sub)
        font_coords = FontProperties(fname=active_fonts["regular"], size=base_coords)
    else:
        font_main = FontProperties(family="monospace", weight="bold", size=base_main)
        font_sub = FontProperties(family="monospace", size=base_sub)
        font_coords = FontProperties(family="monospace", size=base_coords)

    # City Label
    spaced_city = "  ".join(list(display_city.upper())) if is_latin_script(display_city) else display_city
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes, color=THEME["text"],
            ha="center", fontproperties=font_main, zorder=11)

    # Decorative Line
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, 
            color=THEME["text"], linewidth=1 * scale_factor, zorder=11)

    # Country Label
    ax.text(0.5, 0.10, display_country.upper(), transform=ax.transAxes, color=THEME["text"],
            ha="center", fontproperties=font_sub, zorder=11)

    # Coordinates
    lat, lon = point
    coord_text = f"{abs(lat):.4f}° {'N' if lat>=0 else 'S'} / {abs(lon):.4f}° {'E' if lon>=0 else 'W'}"
    ax.text(0.5, 0.07, coord_text, transform=ax.transAxes, color=THEME["text"],
            alpha=0.7, ha="center", fontproperties=font_coords, zorder=11)

    # --- CUSTOM COMMEMORATIVE TEXT ---
    if custom_text:
        font_custom = FontProperties(fname=active_fonts["light"] if active_fonts else None, 
                                     size=custom_text_size * scale_factor)
        if not active_fonts: font_custom.set_family("monospace")
        
        ax.text(0.5, 0.04, custom_text, transform=ax.transAxes, color=THEME["text"],
                alpha=0.8, ha="center", fontproperties=font_custom, zorder=11)

    # Save
    save_kwargs = {"facecolor": THEME["bg"], "bbox_inches": "tight", "pad_inches": 0.05}
    if output_format.lower() == "png": save_kwargs["dpi"] = 300
    plt.savefig(output_file, format=output_format, **save_kwargs)
    plt.close()
