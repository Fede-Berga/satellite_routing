import json
import math
import time
from typing import Dict, List, Tuple, Self
import networkx as nx
import sns.network as snsntwk
import sns.network_parameters as snsnp
from collections import defaultdict as dd
from networkx.algorithms.flow import build_residual_network
from networkx.algorithms.connectivity import build_auxiliary_node_connectivity
from networkx.classes.function import path_weight
import random
import numpy as np
from collections import defaultdict as dd
from datetime import datetime
import simpy


class BaselineSourceRoutingHeaderBuilder:
    _instance: Self = None
    _graph: nx.DiGraph = None
    _last_update: int = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def get_sr_header(self, src_gs: str, dst_gs: str) -> List[Tuple[int, str]]:

        s_time = time.time()

        sp = nx.shortest_path(
            G=self._graph, source=src_gs, target=dst_gs, weight="weight"
        )

        #print("--- Simple shortest path took %s seconds ---" % (time.time() - s_time))

        port_list = [
            self._graph.edges[sp[i], sp[i + 1]]["out_port"]
            for i in range(1, len(sp[1:]))
        ][::-1]
        satellite_gs_list = sp[1:][::-1]

        return [
            (port, satellite_or_gs)
            for port, satellite_or_gs in zip(port_list, satellite_gs_list)
        ]

    def _set_up_graph_copy_for_routing(self, graph: nx.DiGraph):
        # print('BaselineSourceRoutingHeaderBuilder')
        for u, v in graph.edges:
            uv_data = self._graph.edges[u, v]
            uv_data["weight"] = uv_data["length"]

    def _copy_graph_structure(self, graph: nx.DiGraph) -> nx.DiGraph:
        # copy graph structure and edge attributes
        self._graph = graph.__class__()
        self._graph.add_nodes_from(graph)
        self._graph.add_edges_from(graph.edges(data=True))

        # add data
        for u, v in graph.edges:
            u_data = graph.nodes[u]
            if u_data["type"] != snsntwk.NodeTypes.LEO_SATELLITE:
                continue
            for out_port, out_sat_or_gs in u_data[
                "leo_satellite"
            ].out_sat_or_gs.items():
                if out_sat_or_gs == v:
                    self._graph[u][v]["out_port"] = out_port
                    self._graph[u][v]["buffer_occupation"] = (
                        u_data["leo_satellite"].out_ports[out_port].byte_size
                    )
                    break

    @classmethod
    def instance(cls, env: simpy.Environment, graph: nx.DiGraph, update_freq: int):
        # print('instance BaselineSourceRoutingHeaderBuilder')
        if cls._instance is None:
            cls._instance = super(BaselineSourceRoutingHeaderBuilder, cls).__new__(cls)
        
        if cls._last_update == None or (env.now - cls._last_update) > update_freq:
            #print(f'BaselineSourceRoutingHeaderBuilder: {cls._last_update}')
            cls._instance._copy_graph_structure(graph)
            cls._instance._set_up_graph_copy_for_routing(graph)
            cls._last_update = env.now

        return cls._instance


class NoSmoothingOnBufferSizeSourceRoutingHeaderBuilder(
    BaselineSourceRoutingHeaderBuilder
):
    def _set_up_graph_copy_for_routing(cls, graph: nx.DiGraph):
        # print('NoSmoothingOnBufferSizeSourceRoutingHeaderBuilder')
        for u, v in graph.edges:
            u_data = graph.nodes[u]
            uv_data = cls._graph.edges[u, v]
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


class ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder(
    NoSmoothingOnBufferSizeSourceRoutingHeaderBuilder
):
    _exponential_avg_buffer_occupation: Dict[Tuple[str, int], float] = dd(float)

    def _set_up_graph_copy_for_routing(self, graph: nx.DiGraph):
        # print('ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder')
        for u, v in graph.edges:
            u_data = graph.nodes[u]

            if u_data["type"] != snsntwk.NodeTypes.LEO_SATELLITE:
                continue

            out_port = self._graph[u][v]["out_port"]
            sampling_bo = self._graph[u][v]["buffer_occupation"]
            estimated_bo = self._exponential_avg_buffer_occupation[u, out_port]
            self._exponential_avg_buffer_occupation[u, out_port] = (
                snsnp.NetworkParameters.ALPHA * sampling_bo
                + (1 - snsnp.NetworkParameters.ALPHA) * estimated_bo
            )
            # print(f'{u}, {v} : {self._exponential_avg_buffer_occupation[u, out_port]}')
            self._graph[u][v][
                "buffer_occupation"
            ] = self._exponential_avg_buffer_occupation[u, out_port]

        # print(json.dumps(dict((':'.join(str(k)), v) for k,v in self._exponential_avg_buffer_occupation.items()), indent=4))

        super(
            ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder, self
        )._set_up_graph_copy_for_routing(graph)


class KShortestNodeDisjointSourceRoutingHeaderBuilder(
    ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder
):
    _all_couples_shortest_paths = dd(dict)

    def get_sr_header(self, src_gs: str, dst_gs: str) -> List[Tuple[int, str]]:
        s_time = time.time()
        sp_s = self._all_couples_shortest_paths[src_gs][dst_gs]

        sp = None

        if len(sp_s) == 1:
            sp = sp_s[0]
        else:
            total_path_weights = sum(
                [path_weight(self._graph, path, weight="weight") for path in sp_s]
            )

            weights = [
                    1
                    - (path_weight(self._graph, path, weight="weight") / total_path_weights)
                    for path in sp_s
                ]

            sp = random.choices(population=sp_s, weights=weights)[0]
        
        #print("--- Extracting shortest path from cache %s seconds ---" % (time.time() - s_time))

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
    def instance(cls, env: simpy.Environment, graph: nx.DiGraph, update_freq: int):
        if cls._last_update == None or (env.now - cls._last_update) > update_freq:
            super().instance(env, graph, update_freq)
            cls._graph = cls._instance._graph
            cls._last_update = cls._instance._last_update

            s_time = time.time()

            auxiliary = build_auxiliary_node_connectivity(cls._graph)
            residual = build_residual_network(auxiliary, "capacity")

            for src_gs, s_info in graph.nodes(data=True):
                if s_info["type"] == snsntwk.NodeTypes.LEO_SATELLITE:
                    continue
                for dst_gs, t_info in graph.nodes(data=True):
                    if (
                        t_info["type"] == snsntwk.NodeTypes.LEO_SATELLITE
                        or src_gs == dst_gs
                    ):
                        continue

                    src_sat = list(cls._graph[src_gs].keys())[0]
                    dst_sat = list(cls._graph[dst_gs].keys())[0]

                    if src_sat == dst_sat:
                        cls._all_couples_shortest_paths[src_gs][dst_gs] = [
                            [src_gs, src_sat, dst_gs]
                        ]
                    else:
                        sp_s = list(
                            nx.node_disjoint_paths(
                                cls._graph,
                                s=src_sat,
                                t=dst_sat,
                                auxiliary=auxiliary,
                                residual=residual,
                            )
                        )

                        cls._all_couples_shortest_paths[src_gs][dst_gs] = [
                            [src_gs] + sp + [dst_gs] for sp in sp_s
                        ]

            #print(json.dumps(cls._all_couples_shortest_paths, indent=4))
            print(
                "--- All node disjoint paths cache took %s seconds ---" % (time.time() - s_time)
            )

            cls._last_update = env.now

        return cls._instance
