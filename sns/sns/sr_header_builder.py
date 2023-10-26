import networkx as nx
from sns.leo_satellite import LeoSatellite
from typing import List, Tuple


class SourceRoutingHeaderBuilder:
    _instance = None
    _ntwk_graph = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def __get_list_ports(self, path: List[str]):

        port_list = []
        for i in range(1, len(path[1:])):
            hop, next_hop = path[i], path[i + 1]
            hop_ntwk_object: LeoSatellite = self._ntwk_graph.nodes[hop]['leo_satellite']
            for out_port_number, out_port in hop_ntwk_object.out_ports.items():
                next_hop_ntwk_obj = self._ntwk_graph.nodes[next_hop][
                    'leo_satellite' if self._ntwk_graph.nodes[next_hop]['type'] == "LEO_SATELLITE" else 'packet_sink'
                ]
                if out_port.out.out == next_hop_ntwk_obj:
                    port_list.append(out_port_number)
                    continue

        return port_list[::-1]

    def get_sr_header(self, src_gs: str, dst_gs: str) -> List[Tuple[int, str]]:
        sp = nx.shortest_path(G=self._ntwk_graph, source=src_gs, target=dst_gs, weight='length')

        port_list = self.__get_list_ports(sp)
        satellite_gs_list = sp[1:][::-1]
        return [(port, satellite_or_gs) for port, satellite_or_gs in zip(port_list, satellite_gs_list)]


    @classmethod
    def instance(cls, ntwk_graph: nx.DiGraph):
        cls._ntwk_graph = ntwk_graph
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance
