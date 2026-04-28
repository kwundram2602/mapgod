"""Interaktives Rendering mit leafmap (Fallback: Folium)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mapgod.map import Map

from mapgod.layers.vector import VectorLayer
from mapgod.layers.raster import RasterLayer


def _build_leafmap(m: Map):
    import leafmap

    lm = leafmap.Map(
        center=_center(m),
        zoom=_zoom_guess(m),
        draw_control=False,
        measure_control=False,
    )
    if m.basemap is False:
        lm.add_basemap("HYBRID")
    elif isinstance(m.basemap, str):
        lm.add_basemap(m.basemap)
    for layer in m._sorted_layers():
        if isinstance(layer, VectorLayer):
            _add_vector_leafmap(lm, layer)
        elif isinstance(layer, RasterLayer):
            _add_raster_leafmap(lm, layer)
    return lm


def _add_vector_leafmap(lm, layer: VectorLayer) -> None:
    style = {}
    if "color" in layer.style:
        style["color"] = layer.style["color"]
    if "linewidth" in layer.style:
        style["weight"] = layer.style["linewidth"]
    if "alpha" in layer.style:
        style["fillOpacity"] = layer.style["alpha"]
    lm.add_gdf(
        layer.gdf,
        layer_name=layer.label or "Vector",
        style=style or None,
        info_mode="on_click",
    )


def _add_raster_leafmap(lm, layer: RasterLayer) -> None:
    lm.add_raster(
        str(layer.source),
        band=layer.band,
        colormap=layer.cmap,
        layer_name=layer.label or "Raster",
        opacity=layer.alpha,
        vmin=layer.vmin,
        vmax=layer.vmax,
    )


def _build_folium(m: Map):
    import folium

    center = _center(m)
    fm = folium.Map(location=center, zoom_start=_zoom_guess(m))
    for layer in m._sorted_layers():
        if isinstance(layer, VectorLayer):
            tooltip = (
                folium.GeoJsonTooltip(fields=layer.tooltip_fields)
                if layer.tooltip_fields
                else None
            )
            style_fn = _folium_style_fn(layer.style)
            folium.GeoJson(
                layer.gdf.__geo_interface__,
                name=layer.label or "Vector",
                style_function=style_fn,
                tooltip=tooltip,
            ).add_to(fm)
        elif isinstance(layer, RasterLayer):
            import numpy as np
            from matplotlib import cm

            data, meta = layer.read_array()
            bounds_raw = meta["bounds"]
            bounds = [[bounds_raw[1], bounds_raw[0]], [bounds_raw[3], bounds_raw[2]]]
            cmap_fn = cm.get_cmap(layer.cmap)
            vmin = layer.vmin if layer.vmin is not None else np.nanmin(data)
            vmax = layer.vmax if layer.vmax is not None else np.nanmax(data)
            norm = (data - vmin) / (vmax - vmin + 1e-10)
            norm = np.clip(norm, 0, 1)
            rgba = cmap_fn(norm)
            rgba[..., 3] = np.where(np.isnan(data), 0, layer.alpha)
            folium.raster_layers.ImageOverlay(
                image=rgba,
                bounds=bounds,
                name=layer.label or "Raster",
                opacity=1.0,
            ).add_to(fm)
    folium.LayerControl().add_to(fm)
    return fm


def _folium_style_fn(style: dict):
    mapped = {}
    if "color" in style:
        mapped["fillColor"] = style["color"]
        mapped["color"] = style.get("edgecolor", style["color"])
    if "linewidth" in style:
        mapped["weight"] = style["linewidth"]
    if "alpha" in style:
        mapped["fillOpacity"] = style["alpha"]
    return lambda feature: mapped


def render_interactive(m: Map):
    try:
        return _build_leafmap(m)
    except ImportError:
        return _build_folium(m)


def save_interactive(m: Map, path: str | Path) -> None:
    path = Path(path)
    try:
        lm = _build_leafmap(m)
        lm.to_html(str(path))
    except ImportError:
        fm = _build_folium(m)
        fm.save(str(path))


def _center(m: Map) -> list[float]:
    b = m.bounds
    if b is None:
        return [51.0, 10.0]
    return [(b[1] + b[3]) / 2, (b[0] + b[2]) / 2]


def _zoom_guess(m: Map) -> int:
    b = m.bounds
    if b is None:
        return 6
    span = max(b[2] - b[0], b[3] - b[1])
    if span > 50:
        return 3
    elif span > 10:
        return 5
    elif span > 1:
        return 8
    elif span > 0.1:
        return 11
    else:
        return 14
