from pathlib import Path
import datetime
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository
from topology_builder.builder.min_distance_topology_builder import (
    MinimumDistanceTopologyBuilder,
)
from topology_builder.builder.los_topology_builder import LOSTopologyBuilder



class TestLOSTopoBuilder:

    def test_los_topology_builder_(self):
        gs_s = [
            {"name": "Aberdeen", "lat": 57.9, "lon": 2.9},
            {"name": "Bombai", "lat": 19.0, "lon": 72.48},
        ]

        dt = 60000

        now = datetime.datetime.strptime(
            "2023-09-12 10:00:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
        )

        end_time = datetime.datetime.strptime(
            "2023-09-12 10:30:00 +00:00", "%Y-%m-%d %H:%M:%S %z"
        )

        current_topology = (
            MinimumDistanceTopologyBuilder(verbose=False, name="Iridium", t=now)
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))
            )
            .add_GSs(gs_s)
            .add_GSLs()
            .build()
        )

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
                    STKLeoSatelliteRepository(Path("../constellations/Iridium_TLE.txt"))
                )
                .add_GSs(gs_s)
                .add_GSLs()
                .build()
            )

            for gs in current_topology.get_GSs():
                print(gs)
                print(list(current_topology.ntwk.neighbors(gs)))
                assert len(list(current_topology.ntwk.neighbors(gs))) == 1

            now += datetime.timedelta(milliseconds=dt)