from mapgod.layers.vector import VectorLayer
from mapgod.layers.raster import RasterLayer


def test_vector_layer_class_exists():
    assert VectorLayer.kind == "vector"


def test_raster_layer_class_exists():
    assert RasterLayer.kind == "raster"


def test_raster_bounds_reprojects_utm_to_wgs84(sample_raster_utm):
    layer = RasterLayer(sample_raster_utm, target_crs="EPSG:4326")
    b = layer.bounds
    # UTM fixture (500_000, 5_400_000, 600_000, 5_500_000) in EPSG:32632
    # reprojects to approximately (8.57, 48.73, 9.43, 49.62) in WGS-84
    assert 7.0 <= b[0] <= 10.0, f"minx should be ~8.57°, got {b[0]}"
    assert 47.0 <= b[1] <= 51.0, f"miny should be ~48.73°, got {b[1]}"
    assert 7.0 <= b[2] <= 11.0, f"maxx should be ~9.43°, got {b[2]}"
    assert 48.0 <= b[3] <= 51.0, f"maxy should be ~49.62°, got {b[3]}"


def test_raster_bounds_same_crs_unchanged(sample_raster_wgs84):
    layer = RasterLayer(sample_raster_wgs84, target_crs="EPSG:4326")
    b = layer.bounds
    assert b is not None
    assert abs(b[0] - 8.0) < 0.01
    assert abs(b[1] - 48.0) < 0.01
    assert abs(b[2] - 9.0) < 0.01
    assert abs(b[3] - 49.0) < 0.01
