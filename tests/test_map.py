import geopandas as gpd
from shapely.geometry import Point

from mapgod import Map


def test_map_instantiation():
    m = Map(title="Test", crs="EPSG:4326")
    assert m.title == "Test"
    assert m.crs == "EPSG:4326"
    assert m._layers == []


def test_map_repr():
    m = Map(title="Test")
    assert "Map(title='Test'" in repr(m)


def test_map_bounds_empty():
    m = Map()
    assert m.bounds is None


def test_sorted_layers_rasters_first(sample_raster_wgs84):
    gdf = gpd.GeoDataFrame(geometry=[Point(8.5, 48.5)], crs="EPSG:4326")
    m = Map()
    m.add_vector(gdf)              # vector added first
    m.add_raster(sample_raster_wgs84)  # raster added second
    ordered = m._sorted_layers()
    assert ordered[0].kind == "raster"
    assert ordered[1].kind == "vector"


def test_sorted_layers_preserves_single_type(sample_raster_wgs84):
    m = Map()
    m.add_raster(sample_raster_wgs84)
    assert len(m._sorted_layers()) == 1
    assert m._sorted_layers()[0].kind == "raster"


def test_map_mode_default():
    m = Map()
    assert m.mode == "interactive"


def test_map_mode_static():
    m = Map(mode="static")
    assert m.mode == "static"


def test_save_html_routes_to_interactive(tmp_path):
    m = Map(mode="static")
    path = tmp_path / "out.html"
    result = m.save(path)
    assert result == path


def test_save_png_routes_to_static(tmp_path):
    m = Map(mode="interactive")
    path = tmp_path / "out.png"
    result = m.save(path)
    assert result == path
