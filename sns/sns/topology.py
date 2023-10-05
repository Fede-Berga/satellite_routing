from enum import Enum
import json
from typing import Any, List, Self, Tuple
from click import Path
import networkx as nx
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from ns.switch.switch import SimplePacketSwitch


class NodeTypes(str, Enum):
    GROUD_STATION = "GROUD_STATION"
    LEO_SATELLITE = "LEO_SATELLITE"


class Topology:
    def __init__(self, graph: nx.Graph) -> None:
        self.graph = graph

    def __str__(self) -> str:
        return f"Network: {json.dumps(nx.node_link_data(self.graph), indent=4, default=lambda o: f'{type(o)}')}"

    def __repr__(self) -> str:
        return self.__str__()

    def get_GSs(self) -> List[Tuple[Any, Any]]:
        return [
            (node, info)
            for node, info in self.graph.nodes(data=True)
            if info["type"] == NodeTypes.GROUD_STATION
        ]

    def get_leo_satellites(self) -> List[Tuple[Any, Any]]:
        return [
            (node, info)
            for node, info in self.graph.nodes(data=True)
            if info["type"] == NodeTypes.LEO_SATELLITE
        ]

    def get_shortest_path(
        self, source: str, target: str, weight=None
    ) -> Tuple[List[str], int]:
        return (
            nx.shortest_path(G=self.graph, source=source, target=target, weight=weight),
            nx.shortest_path_length(
                G=self.graph, source=source, target=target, weight=weight
            ),
        )

    @classmethod
    def from_json(cls, file: Path) -> Self:
        with open(file, "r") as f:
            data = json.loads(f.read())

        nx_obj = data["networkx_obj"]

        return cls(graph=nx.node_link_graph(nx_obj))

    @classmethod
    def from_topology_builder_svc(cls):
        # TODO
        print("todo")
