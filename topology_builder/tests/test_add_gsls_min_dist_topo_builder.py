import datetime
from pathlib import Path
import pytest
import pytz
from topology_builder.topology.topology import Topology
from topology_builder.builder.min_distance_topology_builder import (
    MinimumDistanceTopologyBuilder,
)
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository


class TestAddGSLs:
    def test_add_GSLs_no_sat(self):
        gs_s = [
            {"name": "Aberdeen", "lat": 57.9, "lon": 2.9},
            {"name": "Bombai", "lat": 19.0, "lon": 72.48},
        ]
        with pytest.raises(Exception):
            _: Topology = (
                MinimumDistanceTopologyBuilder(
                    verbose=True,
                    name="Iridium",
                    t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
                )
                .add_GSs(gs_s)
                .add_GSLs()
                .build()
            )

    def test_add_GSLs_no_gs(self):
        with pytest.raises(Exception):
            _: Topology = (
                MinimumDistanceTopologyBuilder(
                    verbose=True,
                    name="Iridium",
                    t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
                )
                .add_LEO_constellation(
                    STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))
                )
                .add_GSLs()
                .build()
            )

    def test_add_GSLs_basic(self):
        gs_s = [
            {"name": "Aberdeen", "lat": 57.9, "lon": 2.9},
            {"name": "Bombai", "lat": 19.0, "lon": 72.48},
        ]

        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))
            )
            .add_GSs(gs_s)
            .add_GSLs()
            .build()
        )

        print(topology.get_GSLs())

        assert len(topology.get_GSLs()) == 2
