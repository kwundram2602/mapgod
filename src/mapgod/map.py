"""Zentrale Map-Klasse – einheitliche API für Vektor- und Rasterdaten."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import geopandas as gpd

from mapgod.layers.vector import VectorLayer
from mapgod.layers.raster import RasterLayer


class Map:
    """Kartenobjekt, das Layer sammelt und über verschiedene Backends rendert.

    Parameters
    ----------
    title : str
        Kartentitel (wird in statischen Plots als Überschrift angezeigt).
    crs : str
        Ziel-CRS für alle Layer (default: EPSG:4326).
    basemap : str | bool
        Basemap-Tile-Provider für contextily / leafmap.
        ``True`` = OpenStreetMap, ``False`` = keine, oder ein String wie
        ``"CartoDB.Positron"``.
    figsize : tuple[float, float]
        Größe für statische Matplotlib-Plots in Zoll.
    """

    def __init__(
        self,
        title: str = "",
        mode: Literal["static", "interactive"] = "interactive",
        crs: str = "EPSG:4326",
        basemap: str | bool = True,
        figsize: tuple[float, float] = (12, 8),
    ) -> None:
        self.title = title
        self.mode = mode
        self.crs = crs
        self.basemap = basemap
        self.figsize = figsize
        self._layers: list[VectorLayer | RasterLayer] = []

    def add_vector(
        self,
        source: str | Path | gpd.GeoDataFrame,
        *,
        style: dict[str, Any] | None = None,
        label: str | None = None,
        tooltip_fields: list[str] | None = None,
    ) -> Map:
        layer = VectorLayer(
            source=source,
            style=style or {},
            label=label,
            tooltip_fields=tooltip_fields,
            target_crs=self.crs,
        )
        self._layers.append(layer)
        return self

    def add_raster(
        self,
        source: str | Path,
        *,
        band: int = 1,
        cmap: str = "viridis",
        alpha: float = 0.7,
        label: str | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
    ) -> Map:
        layer = RasterLayer(
            source=source,
            band=band,
            cmap=cmap,
            alpha=alpha,
            label=label,
            vmin=vmin,
            vmax=vmax,
            target_crs=self.crs,
        )
        self._layers.append(layer)
        return self

    def _sorted_layers(self) -> list[VectorLayer | RasterLayer]:
        rasters = [layer for layer in self._layers if isinstance(layer, RasterLayer)]
        vectors = [layer for layer in self._layers if isinstance(layer, VectorLayer)]
        return rasters + vectors

    def show(self, backend: Literal["interactive", "static"] | None = None):
        effective = backend or self.mode
        if effective == "interactive":
            from mapgod.backends.interactive import render_interactive

            return render_interactive(self)
        else:
            from mapgod.backends.static import render_static

            return render_static(self)

    def save(
        self,
        path: str | Path,
        *,
        dpi: int = 150,
        backend: Literal["interactive", "static"] | None = None,
    ) -> Path:
        path = Path(path)
        if backend is None:
            if path.suffix == ".html":
                backend = "interactive"
            elif path.suffix != "":
                backend = "static"
        effective = backend or self.mode
        if effective == "interactive":
            from mapgod.backends.interactive import save_interactive

            save_interactive(self, path)
        else:
            from mapgod.backends.static import save_static

            save_static(self, path, dpi=dpi)
        return path

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        from mapgod.utils.geo import merge_bounds

        all_bounds = [layer.bounds for layer in self._layers if layer.bounds]
        return merge_bounds(all_bounds) if all_bounds else None

    def __repr__(self) -> str:
        n_vec = sum(1 for layer in self._layers if isinstance(layer, VectorLayer))
        n_ras = sum(1 for layer in self._layers if isinstance(layer, RasterLayer))
        return f"Map(title={self.title!r}, mode={self.mode!r}, layers={n_vec}V+{n_ras}R, crs={self.crs!r})"
