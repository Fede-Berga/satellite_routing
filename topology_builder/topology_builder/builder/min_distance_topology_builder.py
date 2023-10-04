from typing import Any, Dict
from skyfield.api import utc
from datetime import datetime
from topology_builder.builder.topology_builder import TopologyBuilder


class MinimumDistanceTopologyBuilder(TopologyBuilder):
    def __init__(
        self, verbose: bool, name: str, t: datetime = datetime.now(tz=utc)
    ) -> None:
        super().__init__(verbose, name, t)

    def _add_inter_plane_links(self, satellite: str) -> Dict[str, Any]:
        return self.get_closer_sat_next_plane(satellite)

    def _get_sat_for_building_gsl(self, gs: str) -> Dict[str, Any]:
        return self._get_closer_satellite_to_gs(gs)
