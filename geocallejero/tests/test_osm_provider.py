# geocallejero/tests/test_osm_provider.py

import sys
import os
import hashlib
import tempfile
import shutil
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from geocallejero.core.osm_provider import OsmProvider


@pytest.fixture
def temp_pbf():
    """Crea un archivo PBF temporal falso para pruebas."""
    tmpdir = tempfile.mkdtemp()
    pbf_path = os.path.join(tmpdir, "test.osm.pbf")
    with open(pbf_path, "wb") as f:
        f.write(b"fake pbf content for testing")
    yield pbf_path, tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestOsmProviderHashAndCache:

    def test_compute_pbf_hash(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        computed = provider.compute_pbf_hash()

        expected = hashlib.sha256(b"fake pbf content for testing").hexdigest()
        assert computed == expected

    def test_hash_is_deterministic(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        h1 = provider.compute_pbf_hash()
        h2 = provider.compute_pbf_hash()

        assert h1 == h2
        assert len(h1) == 64

    def test_is_cache_valid_when_no_cache(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        assert provider.is_cache_valid() is False

    def test_is_cache_valid_with_matching_hash(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        pbf_hash = provider.compute_pbf_hash()
        provider._write_cache_hash(pbf_hash)
        with open(provider.cache_path, "wb") as f:
            f.write(b"fake gpkg content")

        assert provider.is_cache_valid() is True

    def test_is_cache_valid_with_stale_hash(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        provider._write_cache_hash("deadbeefdeadbeef")
        with open(provider.cache_path, "wb") as f:
            f.write(b"fake gpkg content")

        assert provider.is_cache_valid() is False

    def test_is_cache_valid_without_hash_file(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        with open(provider.cache_path, "wb") as f:
            f.write(b"fake gpkg content")

        assert provider.is_cache_valid() is False

    def test_pbf_not_found_raises(self, temp_pbf):
        _, tmpdir = temp_pbf
        with pytest.raises(FileNotFoundError):
            OsmProvider(os.path.join(tmpdir, "no_existe.pbf"), tmpdir)

    def test_cache_path_defaults_to_pbf_directory(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path)

        assert provider.cache_dir == os.path.dirname(pbf_path)
        assert provider.cache_path == os.path.join(
            os.path.dirname(pbf_path), OsmProvider.CACHE_FILENAME
        )

    def test_cache_path_respects_custom_dir(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        custom = os.path.join(tmpdir, "cache")
        os.makedirs(custom, exist_ok=True)
        provider = OsmProvider(pbf_path, custom)

        assert provider.cache_path == os.path.join(custom, OsmProvider.CACHE_FILENAME)


class TestOsmProviderConvert:

    @patch("subprocess.run")
    @patch.object(OsmProvider, "_find_ogr2ogr", return_value="ogr2ogr")
    @patch.object(OsmProvider, "compute_pbf_hash", return_value="abc123hash")
    def test_convert_to_gpkg_calls_ogr2ogr(
        self, mock_hash, mock_find, mock_run, temp_pbf
    ):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = provider.convert_to_gpkg()

        assert result == provider.cache_path
        assert mock_run.call_count >= 1

        first_call_args = mock_run.call_args_list[0][0][0]
        assert "ogr2ogr" in first_call_args or any(
            "ogr2ogr" in str(a) for a in first_call_args
        )
        assert any("points" in str(a) for a in first_call_args)

    @patch("subprocess.run")
    @patch.object(OsmProvider, "_find_ogr2ogr", return_value="ogr2ogr")
    def test_convert_to_gpkg_handles_ogr2ogr_error(
        self, mock_find, mock_run, temp_pbf
    ):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        mock_run.return_value = MagicMock(
            returncode=1, stderr="OGRErr: Invalid data source"
        )

        with pytest.raises(RuntimeError, match="ogr2ogr falló"):
            provider.convert_to_gpkg()

    @patch.object(OsmProvider, "is_cache_valid", return_value=True)
    def test_load_or_convert_uses_cache_when_valid(self, mock_valid, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        result = provider.load_or_convert()

        assert result == provider.cache_path

    @patch.object(OsmProvider, "is_cache_valid", return_value=False)
    @patch.object(OsmProvider, "convert_to_gpkg")
    def test_load_or_convert_rebuilds_when_invalid(
        self, mock_convert, mock_valid, temp_pbf
    ):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        mock_convert.return_value = provider.cache_path
        result = provider.load_or_convert()

        assert result == provider.cache_path
        mock_convert.assert_called_once()


class TestOsmProviderNearestPoints:

    @patch("geocallejero.core.osm_provider.QGIS_AVAILABLE", True)
    def test_nearest_points_without_index_raises(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        with pytest.raises(RuntimeError, match="build_spatial_index"):
            provider.nearest_points(0.0, 0.0)

    @patch("geocallejero.core.osm_provider.QGIS_AVAILABLE", True)
    @patch("geocallejero.core.osm_provider.QgsVectorLayer", create=True)
    @patch("geocallejero.core.osm_provider.QgsSpatialIndex", create=True)
    @patch("geocallejero.core.osm_provider.QgsPointXY", create=True)
    @patch.object(OsmProvider, "load_or_convert")
    def test_nearest_points_finds_neighbors(
        self, mock_load, mock_point_cls, mock_index_cls, mock_layer_cls, temp_pbf
    ):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        mock_load.return_value = provider.cache_path

        mock_layer = MagicMock()
        mock_layer.isValid.return_value = True
        mock_layer.featureCount.return_value = 2
        mock_layer_cls.return_value = mock_layer

        from geocallejero.core.osm_provider import QgsPointXY

        geom1 = MagicMock()
        geom1.isEmpty.return_value = False
        geom1.asPoint.return_value = QgsPointXY(-70.1, -20.2)

        geom2 = MagicMock()
        geom2.isEmpty.return_value = False
        geom2.asPoint.return_value = QgsPointXY(-70.15, -20.25)

        feat1 = MagicMock()
        feat1.id.return_value = 0
        feat1.geometry.return_value = geom1
        feat1.__getitem__.side_effect = lambda k: {
            "osm_id": "111",
            "addr_housenumber": "1234",
            "addr_street": "Arturo Prat",
            "addr_city": "Iquique",
            "addr_postcode": "1100000",
        }.get(k)

        feat2 = MagicMock()
        feat2.id.return_value = 1
        feat2.geometry.return_value = geom2
        feat2.__getitem__.side_effect = lambda k: {
            "osm_id": "222",
            "addr_housenumber": "567",
            "addr_street": "Arturo Prat",
            "addr_city": "Iquique",
            "addr_postcode": "1100000",
        }.get(k)

        mock_layer.getFeatures.return_value = [feat1, feat2]

        mock_index = MagicMock()
        mock_index.nearestNeighbor.return_value = [0, 1]
        mock_index_cls.return_value = mock_index

        mock_point_cls.return_value.distance.return_value = 0.0

        provider.build_spatial_index()

        results = provider.nearest_points(-70.1, -20.2, max_results=5)

        assert len(results) == 2
        assert results[0]["housenumber"] == "1234"
        assert results[0]["source"] == "osm_exact"
        assert results[0]["distance"] == 0.0

    @patch("geocallejero.core.osm_provider.QGIS_AVAILABLE", True)
    @patch("geocallejero.core.osm_provider.QgsVectorLayer", create=True)
    @patch("geocallejero.core.osm_provider.QgsSpatialIndex", create=True)
    @patch.object(OsmProvider, "load_or_convert")
    def test_feature_count(self, mock_load, mock_index_cls, mock_layer_cls, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        mock_load.return_value = provider.cache_path
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = True
        mock_layer.featureCount.return_value = 42
        mock_layer_cls.return_value = mock_layer
        mock_index_cls.return_value = MagicMock()

        assert provider.feature_count == 0

        provider.build_spatial_index()

        assert provider.feature_count == 42

    def test_has_index_before_build(self, temp_pbf):
        pbf_path, tmpdir = temp_pbf
        provider = OsmProvider(pbf_path, tmpdir)

        assert provider.has_index() is False
