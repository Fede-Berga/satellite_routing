from pathlib import Path
import datetime, pytz
import pytest
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository
from topology_builder.topology.topology import Topology
from topology_builder.builder.min_distance_topology_builder import (
    MinimumDistanceTopologyBuilder,
)


class TestAddISLs:
    def test_add_isls(self):
        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))
            )
            .add_ISLs()
            .build()
        )

        print(topology)

        for sat in topology.get_leo_satellites():
            assert len(list(topology.ntwk.adj[sat])) == 4

        assert topology.get_ISLs() != 0

    def test_add_isls_no_sat(self):
        with pytest.raises(Exception):
            topology: Topology = (
                MinimumDistanceTopologyBuilder(
                    verbose=True,
                    name="Iridium",
                    t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
                )
                .add_ISLs()
                .build()
            )
