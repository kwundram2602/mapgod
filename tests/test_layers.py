from mapgod.layers.vector import VectorLayer
from mapgod.layers.raster import RasterLayer


def test_vector_layer_class_exists():
    assert VectorLayer.kind == "vector"


def test_raster_layer_class_exists():
    assert RasterLayer.kind == "raster"


def test_raster_bounds_reprojects_utm_to_wgs84(sample_raster_utm):
    layer = RasterLayer(sample_raster_utm, target_crs="EPSG:4326")
    b = layer.bounds
    assert b is not None
    # All four values must be valid WGS-84 degrees, not UTM meters
    assert -180 <= b[0] <= 180, f"minx out of range: {b[0]}"
    assert -90  <= b[1] <= 90,  f"miny out of range: {b[1]}"
    assert -180 <= b[2] <= 180, f"maxx out of range: {b[2]}"
    assert -90  <= b[3] <= 90,  f"maxy out of range: {b[3]}"


def test_raster_bounds_same_crs_unchanged(sample_raster_wgs84):
    layer = RasterLayer(sample_raster_wgs84, target_crs="EPSG:4326")
    b = layer.bounds
    assert b is not None
    assert abs(b[0] - 8.0) < 0.01
    assert abs(b[1] - 48.0) < 0.01
    assert abs(b[2] - 9.0) < 0.01
    assert abs(b[3] - 49.0) < 0.01
