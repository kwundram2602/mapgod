"""Statisches Rendering mit Matplotlib + contextily."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from mapgod.map import Map


def _resolve_basemap(basemap: str | bool):
    if basemap is False:
        return None
    try:
        import contextily as cx
    except ImportError:
        return None
    if basemap is True:
        return cx.providers.OpenStreetMap.Mapnik
    parts = basemap.split(".")
    provider = cx.providers
    for part in parts:
        provider = provider[part]
    return provider


def _build_figure(m: Map):
    fig, ax = plt.subplots(figsize=m.figsize)
    for layer in m._sorted_layers():
        layer.plot_on(ax)
    provider = _resolve_basemap(m.basemap)
    if provider is not None:
        try:
            import contextily as cx

            if m.crs != "EPSG:3857":
                cx.add_basemap(ax, crs=m.crs, source=provider, attribution_size=6)
            else:
                cx.add_basemap(ax, source=provider, attribution_size=6)
        except Exception as exc:
            import warnings

            warnings.warn(f"Basemap konnte nicht geladen werden: {exc}")
    if m.title:
        ax.set_title(m.title, fontsize=14, fontweight="bold")
    ax.set_axis_off()
    fig.tight_layout()
    return fig, ax


def render_static(m: Map):
    fig, ax = _build_figure(m)
    plt.show()
    return fig


def save_static(m: Map, path: str | Path, dpi: int = 150) -> None:
    fig, ax = _build_figure(m)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
