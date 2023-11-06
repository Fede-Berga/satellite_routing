from enum import Enum
import json
import math
from typing import Dict, List, Tuple, Self
import sns.network as snsnet
import sns.leo_satellite as snsleo
import networkx as nx
import sns.network as snsntwk
import sns.network_parameters as snsnp
from collections import defaultdict as dd

class HeaderBuilderAlgorithm(str, Enum):
    SHORTEST_PATH = "SHORTEST_PATH"
    SHORTEST_PATH_INTEGRATING_BUFFER_OCCUPATION = "SHORTEST_PATH_INTEGRATING_BUFFER_OCCUPATION"
    SHORTEST_PATH_INTEGRATING_BUFFER_OCCUPATION_EXPONENTIAL_SMOOTHING = "SHORTEST_PATH_INTEGRATING_BUFFER_OCCUPATION_EXPONENTIAL_SMOOTHING"


class SourceRoutingHeaderBuilder:
    _instance: Self = None
    _graph: nx.DiGraph = None
    _exponential_avg_buffer_occupation: Dict[Tuple[str, int], float] = dd(float)

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def get_sr_header(self, src_gs: str, dst_gs: str) -> List[Tuple[int, str]]:
        sp = nx.shortest_path(
            G=self._graph, source=src_gs, target=dst_gs, weight="weight"
        )

        port_list = [
            self._graph.edges[sp[i], sp[i + 1]]["out_port"]
            for i in range(1, len(sp[1:]))
        ][::-1]
        satellite_gs_list = sp[1:][::-1]

        return [
            (port, satellite_or_gs)
            for port, satellite_or_gs in zip(port_list, satellite_gs_list)
        ]

    @classmethod
    def __exponential_smoothing(
        cls, graph: nx.DiGraph, copy_graph: nx.DiGraph
    ) -> nx.DiGraph:
        for u, v in graph.edges:
            u_data = graph.nodes[u]

            if u_data["type"] != snsntwk.NodeTypes.LEO_SATELLITE:
                continue

            out_port = copy_graph[u][v]["out_port"]
            bo = copy_graph[u][v]["buffer_occupation"]
            cls._exponential_avg_buffer_occupation[u, out_port] = (
                1 - snsnp.NetworkParameters.ALPHA
            ) * cls._exponential_avg_buffer_occupation[
                u, out_port
            ] + snsnp.NetworkParameters.ALPHA * bo
            copy_graph[u][v][
                "buffer_occupation"
            ] = cls._exponential_avg_buffer_occupation[u, out_port]

        return cls.__no_smoothing(graph, copy_graph)

    @classmethod
    def __no_smoothing(cls, graph: nx.DiGraph, copy_graph: nx.DiGraph) -> nx.DiGraph:
        for u, v in graph.edges:
            u_data = graph.nodes[u]
            uv_data = copy_graph.edges[u, v]
            buffer_factor = 0
            if u_data["type"] == snsntwk.NodeTypes.LEO_SATELLITE:
                try:
                    buffer_factor = 1 / (
                        1
                        - (
                            uv_data["buffer_occupation"]
                            / snsnp.NetworkParameters.SATELLITE_QUEUE_SIZE
                        )
                    )
                except:
                    buffer_factor = math.inf
            if abs(uv_data["length"] + buffer_factor) > (2**31 - 1):
                uv_data["weight"] = math.inf
            else:
                uv_data["weight"] = uv_data["length"] + buffer_factor

        return copy_graph

    @classmethod
    def __baseline(cls, graph: nx.DiGraph, copy_graph: nx.DiGraph) -> nx.DiGraph:
        for u, v in graph.edges:
            uv_data = copy_graph.edges[u, v]
            uv_data["weight"] = uv_data["length"]

        return copy_graph

    @classmethod
    def graph_copy(cls, graph: nx.DiGraph) -> nx.DiGraph:
        # copy graph structure and edge attributes
        copy_graph = graph.__class__()
        copy_graph.add_nodes_from(graph)
        copy_graph.add_edges_from(graph.edges(data=True))

        # add data
        for u, v in graph.edges:
            u_data = graph.nodes[u]
            if u_data["type"] != snsntwk.NodeTypes.LEO_SATELLITE:
                continue
            for out_port, out_sat_or_gs in u_data[
                "leo_satellite"
            ].out_sat_or_gs.items():
                if out_sat_or_gs == v:
                    copy_graph[u][v]["out_port"] = out_port
                    copy_graph[u][v]["buffer_occupation"] = (
                        u_data["leo_satellite"].out_ports[out_port].byte_size
                    )
                    break

        return cls.__baseline(graph, copy_graph)

    @classmethod
    def instance(cls, graph: nx.DiGraph):
        cls._graph = cls.graph_copy(graph)
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

#class BaselineSourceRoutingHeaderBuilder(SourceRoutingHeaderBuilder):
    
