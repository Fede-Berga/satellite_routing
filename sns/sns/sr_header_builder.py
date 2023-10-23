import networkx as nx
from sns.network import Network, NodeTypes
from sns.leo_satellite import LeoSatellite


class SourceRoutingHeaderBuilder:
    _instance = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def get_route_list_of_ports(self, src_gs: str, dst_gs: str, ntwk: Network):

        sp, _ = ntwk.get_shortest_path(
            source=src_gs, target=dst_gs, weight="length"
        )

        port_list = []
        for i in range(1, len(sp[1:])):
            hop, next_hop = sp[i], sp[i + 1]
            hop_ntwk_object: LeoSatellite = ntwk.graph.nodes[hop]['leo_satellite']
            for out_port_number, out_port in hop_ntwk_object.out_ports.items():
                next_hop_ntwk_obj = ntwk.graph.nodes[next_hop][
                    'leo_satellite' if ntwk.graph.nodes[next_hop]['type'] == NodeTypes.LEO_SATELLITE else 'packet_sink'
                ]
                if out_port.out.out == next_hop_ntwk_obj:
                    port_list.append(out_port_number)
                    continue
        
        print(port_list)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            print("Creating new instance")
            cls._instance = cls.__new__(cls)
            # Put any initialization here.
        return cls._instance
