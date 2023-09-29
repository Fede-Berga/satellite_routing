import os
from pathlib import Path
import sys
from skyfield.api import EarthSatellite

sys.path.append(os.path.abspath('./topology_builder'))

from topology_builder.satellite_repository import STKLeoSatelliteRepository

class TestSatelliteRepository:

    def test_skt_repo_simple_import(self):

        repo = STKLeoSatelliteRepository(Path('./constellations/Iridium_TLE.txt'))

        assert len(repo.get_constellation()) == 66
    
    def test_stk_repo_check_epoch(self):

        satellites = STKLeoSatelliteRepository(Path('./constellations/Iridium_TLE.txt')).get_constellation()

        assert len(set([satellite['satellite'].epoch for satellite in satellites])) == 1