"""Rasterlayer – lädt Raster via rasterio / rioxarray."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class RasterLayer:
    """Wrapper für Rasterdaten mit Darstellungsoptionen."""

    kind = "raster"

    def __init__(
        self,
        source: str | Path,
        band: int = 1,
        cmap: str = "viridis",
        alpha: float = 0.7,
        label: str | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
        target_crs: str = "EPSG:4326",
    ) -> None:
        self.source = Path(source)
        self.band = band
        self.cmap = cmap
        self.alpha = alpha
        self.label = label or self.source.stem
        self.vmin = vmin
        self.vmax = vmax
        self.target_crs = target_crs
        self._meta = self._read_meta()
        self._bounds_reprojected = self._reproject_bounds()

    def _reproject_bounds(self) -> tuple[float, float, float, float]:
        from rasterio.warp import transform_bounds

        b = self._meta["bounds"]
        src_crs = self._meta["crs"]
        if str(src_crs) == self.target_crs:
            return (b.left, b.bottom, b.right, b.top)
        return transform_bounds(src_crs, self.target_crs, b.left, b.bottom, b.right, b.top)

    def _read_meta(self) -> dict[str, Any]:
        import rasterio

        with rasterio.open(self.source) as src:
            return {
                "crs": src.crs,
                "bounds": src.bounds,
                "transform": src.transform,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": src.dtypes[0],
                "nodata": src.nodata,
            }

    def read_array(self) -> tuple[np.ndarray, dict]:
        import rasterio
        from rasterio.warp import calculate_default_transform, reproject, Resampling

        with rasterio.open(self.source) as src:
            if str(src.crs) != self.target_crs:
                transform, width, height = calculate_default_transform(
                    src.crs, self.target_crs, src.width, src.height, *src.bounds
                )
                data = np.empty((height, width), dtype=src.dtypes[0])
                reproject(
                    source=rasterio.band(src, self.band),
                    destination=data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=self.target_crs,
                    resampling=Resampling.nearest,
                )
                from rasterio.transform import array_bounds

                bounds = array_bounds(height, width, transform)
            else:
                data = src.read(self.band)
                transform = src.transform
                bounds = src.bounds
        nodata = self._meta.get("nodata")
        if nodata is not None:
            data = data.astype(float)
            data[data == nodata] = np.nan
        meta = {"transform": transform, "crs": self.target_crs, "bounds": bounds}
        return data, meta

    def read_xarray(self):
        import rioxarray  # noqa: F401
        import xarray as xr

        da = xr.open_dataarray(self.source, engine="rasterio")
        if str(da.rio.crs) != self.target_crs:
            da = da.rio.reproject(self.target_crs)
        return da.sel(band=self.band)

    def plot_on(self, ax) -> None:
        import matplotlib.pyplot as plt

        data, meta = self.read_array()
        bounds = meta["bounds"]
        extent = [bounds[0], bounds[2], bounds[1], bounds[3]]
        im = ax.imshow(
            data,
            extent=extent,
            cmap=self.cmap,
            alpha=self.alpha,
            vmin=self.vmin,
            vmax=self.vmax,
            origin="upper",
            aspect="auto",
        )
        cbar = plt.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
        if self.label:
            cbar.set_label(self.label)

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        return self._bounds_reprojected

    def __repr__(self) -> str:
        m = self._meta
        return (
            f"RasterLayer({self.label!r}, "
            f"{m['width']}x{m['height']}, "
            f"{m['count']} bands, "
            f"crs={m['crs']})"
        )
