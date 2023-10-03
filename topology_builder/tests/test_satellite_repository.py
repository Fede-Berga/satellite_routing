from pathlib import Path
import pytest
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository


class TestSatelliteRepository:
    def test_stk_repo_simple_import(self):
        repo = STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))

        assert len(repo.get_constellation()) == 66

    def test_stk_repo_check_epoch(self):
        satellites = STKLeoSatelliteRepository(
            Path("../constellations/Iridium_TLE.txt")
        ).get_constellation()

        assert len(set([info["skyfield_obj"].epoch for _, info in satellites])) == 1

    def test_stk_repo_invalid_path(self):
        with pytest.raises(Exception):
            STKLeoSatelliteRepository(Path("invalid/path/file.tle")).get_constellation()
