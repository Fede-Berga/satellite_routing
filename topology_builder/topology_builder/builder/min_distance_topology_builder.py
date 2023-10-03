from typing import Any, Dict, List, Tuple
from skyfield.api import load, wgs84, EarthSatellite, utc
from skyfield.toposlib import GeographicPosition
from datetime import datetime
from topology_builder.repository.satellite_repository import LeoSatelliteRepository
from topology_builder.topology.topology import Topology
from topology_builder.node_types import NodeTypes
from topology_builder.builder.topology_builder import TopologyBuilder


class MinimumDistanceTopologyBuilder(TopologyBuilder):
    def __init__(
        self, verbose: bool, name: str, t: datetime = datetime.now(tz=utc)
    ) -> None:
        super().__init__(verbose, name, t)

    def _add_inter_plane_links(self, satellite: str) -> None:
        # print("inter plane MINDIST...")
        current_plane = self.topology.ntwk.nodes[satellite]["plane"]

        satellites_next_plane_los = [
            x
            for x, y in self.topology.ntwk.nodes(data=True)
            if type(x) == EarthSatellite
            and y["plane"] == (current_plane + 1) % self.topology.no_planes
            and self._los_between_satellites(satellite, x)
        ]

        min_dist_next_plane = min(
            satellites_next_plane_los,
            key=lambda x: (x.at(self.t) - satellite.at(self.t)).distance().km,
        )

        # print(f"min_dist_next_plane: {min_dist_next_plane}")

        self.topology.ntwk.add_edge(
            satellite,
            min_dist_next_plane,
            length=(min_dist_next_plane.at(self.t) - satellite.at(self.t))
            .distance()
            .km,
        )

    def _get_sat_for_building_gsl(self, gs: str) -> Dict[str, Any]:
        return self._get_closer_satellite_to_gs(gs)