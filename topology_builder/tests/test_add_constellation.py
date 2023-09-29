import os
from pathlib import Path
import datetime, pytz
import sys
import pytest
import networkx as nx
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("./topology_builder"))

from topology_builder.satellite_repository import STKLeoSatelliteRepository
from topology_builder.topology import Topology
from topology_builder.topology_builder import (
    MinimumDistanceTopologyBuilder,
    LOSTopologyBuilder,
)


class TestAddConstellation:
    def test_add_constellation(self):
        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            .build()
        )

        assert len(topology.get_satellites()) == 66

    def test_add_isls(self):
        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            .add_ISLs()
            .build()
        )

        #print(topology.get_satellites())
        #print([(sat.name, topology.ntwk.nodes[sat]["plane"]) for sat in topology.get_satellites()])

        assert topology.get_ISLs != 0

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

    def test_add_gsls(self):
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
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            .add_GSs(gs_s)
            .add_GSLs()
            .build()
        )

        print(topology.ntwk.edges)

        assert len(topology.get_GSLs()) == 2

    def test_add_gsls_no_sat(self):
        with pytest.raises(Exception):
            topology: Topology = (
                MinimumDistanceTopologyBuilder(
                    verbose=True,
                    name="Iridium",
                    t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
                )
                .add_GSLs()
                .build()
            )

    def test_los_topology_builder(self):
        gs_s = [
            {"name": "Aberdeen", "lat": 57.9, "lon": 2.9},
            {"name": "Bombai", "lat": 19.0, "lon": 72.48},
        ]

        dt = 1000

        now = datetime.datetime.strptime(
            "2023-09-12 10:00:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
        )

        end_time = datetime.datetime.strptime(
            "2023-09-12 10:30:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
        )

        current_topology = (
            MinimumDistanceTopologyBuilder(verbose=False, name="Iridium", t=now)
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            #.add_GSs(gs_s)
            #.add_GSLs()
            .add_ISLs()
            .build()
        )

        now += datetime.timedelta(milliseconds=dt)

        while now <= end_time:
            print(f"\nBuilding topology at {now}")

            previous_topology = current_topology

            current_topology = (
                MinimumDistanceTopologyBuilder(
                    verbose=False,
                    name="Iridium",
                    t=now,
                    #previous_topology=previous_topology,
                )
                .add_LEO_constellation(
                    STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
                )
                #.add_GSs(gs_s)
                #.add_GSLs()
                .add_ISLs()
                .build()
            )

            for sat in current_topology.get_satellites():
                    if len(list(current_topology.ntwk.neighbors(sat))) != 4:
                        print(sat.name)
                        print(f"{len(list(current_topology.ntwk.neighbors(sat)))}, {list(current_topology.ntwk.neighbors(sat))}")

            now += datetime.timedelta(milliseconds=dt)

    def test_los_topology_builder_isls(self):
            dt = 1000

            now = datetime.datetime.strptime(
                "2023-09-01 00:00:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
            )

            end_time = datetime.datetime.strptime(
                "2023-09-01 00:30:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
            )

            current_topology = (
                MinimumDistanceTopologyBuilder(verbose=False, name="Iridium", t=now)
                .add_LEO_constellation(
                    STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
                )
                .add_ISLs()
                .build()
            )

            for sat in current_topology.get_satellites():
                assert len(list(current_topology.ntwk.neighbors(sat))) == 4 

            now += datetime.timedelta(milliseconds=dt)

            while now <= end_time:
                print(f"\nBuilding topology at {now}")
                
                previous_topology = current_topology

                current_topology = (
                    LOSTopologyBuilder(
                        verbose=False,
                        name="Iridium",
                        t=now,
                        previous_topology=previous_topology,
                    )
                    .add_LEO_constellation(
                        STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
                    )
                    .add_ISLs()
                    .build()
                )

                now += datetime.timedelta(milliseconds=dt)