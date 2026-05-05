"""Trajectory plotting and animation over GeoTIFF rasters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.axes import Axes
from matplotlib.figure import Figure

if TYPE_CHECKING:
    from vecraspy.vector import Trajectory


def _load_raster(
    path: Path | str, band: int
) -> tuple[np.ndarray, list[float], Any]:
    """Return (data_2d, extent, raster_crs) from a GeoTIFF."""
    with rasterio.open(path) as src:
        raw = src.read(band).astype(float)
        nodata = src.nodata
        bounds = src.bounds
        crs = src.crs
    if nodata is not None:
        raw = np.where(raw == nodata, np.nan, raw)
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    return raw, extent, crs


def _reproject_points(
    traj: Trajectory, raster_crs: Any
) -> tuple[list[float], list[float]]:
    """Return (xs, ys) of trajectory points reprojected to raster CRS."""
    epsg = raster_crs.to_epsg()
    target = f"EPSG:{epsg}" if epsg else raster_crs.to_wkt()
    pts = traj.points.to_crs(target) if traj.points.crs else traj.points
    return [g.x for g in pts.geometry], [g.y for g in pts.geometry]


def _color_cycle() -> list[str]:
    return [p["color"] for p in plt.rcParams["axes.prop_cycle"]]


def plot_trajectory(
    raster: Path | str,
    trajectories: Trajectory | list[Trajectory],
    *,
    band: int = 1,
    cmap: str = "gray",
    point_style: dict | None = None,
    line_style: dict | None = None,
    ax: Axes | None = None,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 8),
) -> tuple[Figure, Axes]:
    """Plot one or more trajectories over a GeoTIFF raster (static)."""
    from vecraspy.vector import Trajectory as _Trajectory

    if isinstance(trajectories, _Trajectory):
        trajectories = [trajectories]

    data, extent, raster_crs = _load_raster(raster, band)

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    valid = data[np.isfinite(data)]
    vmin = float(np.nanpercentile(valid, 2)) if valid.size > 0 else None
    vmax = float(np.nanpercentile(valid, 98)) if valid.size > 0 else None
    ax.imshow(data, cmap=cmap, extent=extent, origin="upper", vmin=vmin, vmax=vmax)

    ls: dict = {"linewidth": 1.5, "alpha": 0.8}
    ps: dict = {"markersize": 6, "zorder": 5}
    if line_style:
        ls.update(line_style)
    if point_style:
        ps.update(point_style)

    colors = _color_cycle()
    for i, traj in enumerate(trajectories):
        color = colors[i % len(colors)]
        xs, ys = _reproject_points(traj, raster_crs)
        if len(xs) > 1:
            ax.plot(xs, ys, color=color, **ls)
        ax.plot(xs[-1], ys[-1], "o", color=color, **ps)

    if title:
        ax.set_title(title)
    ax.set_xlabel("Easting")
    ax.set_ylabel("Northing")
    return fig, ax
