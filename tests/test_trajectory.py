"""Tests for mapgod.trajectory."""

from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pytest
import rasterio
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from shapely.geometry import Point

matplotlib.use("Agg")

from vecraspy.vector import Trajectory


def _write_raster(tmp_path: Path) -> Path:
    """Write a 4x4 float32 GeoTIFF in EPSG:4326 covering [0,4] x [0,4]."""
    data = np.arange(16, dtype=np.float32).reshape(4, 4)
    transform = from_bounds(0.0, 0.0, 4.0, 4.0, 4, 4)
    path = tmp_path / "test.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
    ) as dst:
        dst.write(data, 1)
    return path


def _make_trajectory(id=None) -> Trajectory:
    pts = [Point(1.0, 1.0), Point(2.0, 2.0), Point(3.0, 3.0)]
    gdf = gpd.GeoDataFrame({"geometry": pts}, crs="EPSG:4326")
    return Trajectory(id=id, points=gdf)


def test_plot_trajectory_returns_figure_and_axes(tmp_path):
    from mapgod.trajectory import plot_trajectory

    raster = _write_raster(tmp_path)
    traj = _make_trajectory(id="t1")
    fig, ax = plot_trajectory(raster, traj)
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)


def test_plot_trajectory_list_of_trajectories(tmp_path):
    from mapgod.trajectory import plot_trajectory

    raster = _write_raster(tmp_path)
    trajs = [_make_trajectory(id="a"), _make_trajectory(id="b")]
    fig, ax = plot_trajectory(raster, trajs)
    assert isinstance(fig, Figure)


def test_plot_trajectory_accepts_existing_ax(tmp_path):
    import matplotlib.pyplot as plt
    from mapgod.trajectory import plot_trajectory

    raster = _write_raster(tmp_path)
    fig_pre, ax_pre = plt.subplots()
    fig, ax = plot_trajectory(raster, _make_trajectory(), ax=ax_pre)
    assert ax is ax_pre
