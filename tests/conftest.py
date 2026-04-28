# tests/conftest.py
import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


@pytest.fixture()
def sample_raster_utm(tmp_path):
    """2x2 GeoTIFF in EPSG:32632 (UTM zone 32N, coords in meters)."""
    path = tmp_path / "utm.tif"
    transform = from_bounds(500_000, 5_400_000, 600_000, 5_500_000, 2, 2)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(32632),
        transform=transform,
    ) as dst:
        dst.write(np.ones((2, 2), dtype=np.float32), 1)
    return path


@pytest.fixture()
def sample_raster_wgs84(tmp_path):
    """2x2 GeoTIFF already in EPSG:4326."""
    path = tmp_path / "wgs84.tif"
    transform = from_bounds(8.0, 48.0, 9.0, 49.0, 2, 2)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
    ) as dst:
        dst.write(np.ones((2, 2), dtype=np.float32), 1)
    return path
