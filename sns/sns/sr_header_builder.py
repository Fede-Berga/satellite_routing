import networkx as nx
from sns.leo_satellite import LeoSatellite


class SourceRoutingHeaderBuilder:
    _instance = None
    _ntwk_graph = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def get_route_list_of_ports(self, src_gs: str, dst_gs: str):

        sp = nx.shortest_path(G=self._ntwk_graph, source=src_gs, target=dst_gs, weight='length')

        port_list = []
        for i in range(1, len(sp[1:])):
            hop, next_hop = sp[i], sp[i + 1]
            hop_ntwk_object: LeoSatellite = self._ntwk_graph.nodes[hop]['leo_satellite']
            for out_port_number, out_port in hop_ntwk_object.out_ports.items():
                next_hop_ntwk_obj = self._ntwk_graph.nodes[next_hop][
                    'leo_satellite' if self._ntwk_graph.nodes[next_hop]['type'] == "LEO_SATELLITE" else 'packet_sink'
                ]
                if out_port.out.out == next_hop_ntwk_obj:
                    port_list.append(out_port_number)
                    continue

        port_list.reverse()
        return port_list

    @classmethod
    def instance(cls, ntwk_graph: nx.DiGraph):
        cls._ntwk_graph = ntwk_graph
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance
