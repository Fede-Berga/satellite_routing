from typing import Any, Dict
from skyfield.api import utc
from datetime import datetime
from topology_builder.topology.topology import Topology
from topology_builder.builder.topology_builder import TopologyBuilder
from topology_builder.node_types import NodeTypes


class LOSTopologyBuilder(TopologyBuilder):
    def __init__(
        self,
        verbose: bool,
        name: str,
        previous_topology: Topology,
        t: datetime = datetime.now(tz=utc),
    ) -> None:
        super().__init__(verbose, name, t)
        self.previous_topology = previous_topology

    def _add_inter_plane_links(self, satellite: str) -> Dict[str, Any]:
        next_plane = (
            self.topology.get_sat_plane(satellite) + 1
        ) % self.topology.no_planes
        
        candidate_next_plane = next(
            iter(
                [
                    sat
                    for sat in self.previous_topology.ntwk.adj[satellite]
                    if self.previous_topology.ntwk.nodes[sat]["type"]
                    == NodeTypes.LEO_SATELLITE
                    and self.previous_topology.get_sat_plane(sat) == next_plane
                ]
            )
        )
    
        if not self._los_between_satellites(satellite, candidate_next_plane):
            return self.get_closer_sat_next_plane(satellite)

        return {
            "satellite": candidate_next_plane,
            "distance": self.topology.get_difference(candidate_next_plane, satellite)
            .distance()
            .km,
        }

    def _get_sat_for_building_gsl(self, gs: str) -> Dict[str, Any]:
        candidate = next(iter(self.previous_topology.ntwk.adj[gs]))

        alt, _, distance = self.topology.get_difference(candidate, gs).altaz()

        # below the horizon
        if alt.degrees <= 0:
            return self._get_closer_satellite_to_gs(gs)
        else:
            return {"satellite": candidate, "distance": distance.km}
