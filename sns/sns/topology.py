import json
from typing import List
from click import Path
from sns.leo_satellite import LeoSatellite
from sns.ground_station import GroundStation


class Topology:
    def __init__(
        self, 
        all_satellites: List[LeoSatellite] = [], 
        all_gs: List[GroundStation] = []
    ) -> None:
        self.all_satellite: LeoSatellite = all_satellites
        self.all_gs: GroundStation = all_gs

    def __str__(self) -> str:
        return f"LEO satellites: {self.all_satellite}, ground_stations: {self.all_gs}"

    @classmethod
    def from_json(cls, file: Path):
        with open(file, "r") as f:
            data = json.loads(f.read())

        graph = data["graph"]

        return cls(
            all_satellites=[
                LeoSatellite(id=i, name=leo_sat["name"])
                for i, leo_sat in enumerate(graph["satellites"])
            ],
            all_gs=[
                GroundStation(id=i, name=gs["name"])
                for i, gs in enumerate(graph["ground_stations"])
            ],
        )

    @classmethod
    def from_topology_builder_svc(cls):
        # TODO
        print("todo")
    
    @classmethod
    def from_networkx(cls):
        # TODO
        print("todo")
