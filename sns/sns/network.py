import copy
from enum import Enum
import json
from typing import Any, List, Self, Tuple, Dict
from pathlib import Path
import requests
import networkx as nx
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from ns.switch.switch import SimplePacketSwitch
from ns.port.wire import Wire
from ns.port.port import Port
from ns.demux.fib_demux import FIBDemux
import simpy
from scipy import constants


class NodeTypes(str, Enum):
    GROUD_STATION = "GROUD_STATION"
    LEO_SATELLITE = "LEO_SATELLITE"


class Network:
    def __init__(self, graph: nx.DiGraph) -> None:
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

    def __build(self, env: simpy.Environment) -> Self:
        # Set sink
        for _, info in self.get_GSs():
            info["packet_sink"] = PacketSink(env, debug=False)

        # Set packet generators
        for i, (gs, gs_info) in enumerate(self.get_GSs()):
            for j, (target, _) in enumerate(self.get_GSs()):
                if gs == target:
                    continue

                pg = DistPacketGenerator(
                    env,
                    target,
                    lambda: 1.5,
                    lambda: 100.0,
                    flow_id=int(str(i) + str(j)),
                    debug=False,
                )

                if "packet_generator" not in gs_info:
                    gs_info["packet_generator"] = dict()

                gs_info["packet_generator"][target] = pg

        # Set sat switch
        for node, info in self.get_leo_satellites():
            info["switch"] = SimplePacketSwitch(
                env=env,
                nports=self.graph.out_degree[node],
                port_rate=8000,
                buffer_size=8000,
                element_id=node,
            )

        #  isl wire, downstream gsl wire
        for source, s_info in self.get_leo_satellites():
            for i, target in enumerate(list(self.graph.adj[source])):
                delay_dist = self.graph[source][target]["length"] / (constants.c / 1000)

                wire = Wire(
                    env,
                    delay_dist=lambda: delay_dist,
                )

                self.graph[source][target]["out_port"] = i
                self.graph[source][target]["wire"] = wire
                s_info["switch"].ports[i].out = wire

                if self.graph.nodes[target]["type"] == NodeTypes.LEO_SATELLITE:
                    wire.out = self.graph.nodes[target]["switch"]
                else:
                    wire.out = self.graph.nodes[target]["packet_sink"]

        # gs --> sat links
        for gs, info in self.get_GSs():
            upstream_sat = next(iter(list(self.graph.adj[gs])))
            delay_dist = self.graph[gs][upstream_sat]["length"] / (constants.c / 1000)
            for target, pg in info["packet_generator"].items():
                wire = Wire(
                    env,
                    delay_dist=lambda: delay_dist,
                )

                if "wire" not in self.graph[gs][upstream_sat]:
                    self.graph[gs][upstream_sat]["wire"] = dict()
                self.graph[gs][upstream_sat]["wire"][target] = wire

                pg.out = wire
                wire.out = self.graph.nodes[upstream_sat]["switch"]

        # Routing
        self.__set_up_sat_switches_for_routing()

        return self

    def __update(self, env: simpy.Environment, old_ntwk: Self) -> Self:
        # Set sink
        for gs, old_info in old_ntwk.get_GSs():
            self.graph.nodes[gs]["packet_sink"] = old_info["packet_sink"]

        # Set packet generators
        for gs, old_gs_info in old_ntwk.get_GSs():
            for target, _ in old_ntwk.get_GSs():
                if gs == target:
                    continue

                if "packet_generator" not in self.graph.nodes[gs]:
                    self.graph.nodes[gs]["packet_generator"] = dict()

                self.graph.nodes[gs]["packet_generator"][target] = old_gs_info[
                    "packet_generator"
                ][target]

        # Set sat switch
        for node, info in self.get_leo_satellites():
            info["switch"] = old_ntwk.graph.nodes[node]["switch"]

        # isl wire, downstream gsl wire
        for source, s_info in self.get_leo_satellites():
            for target in list(self.graph.adj[source]):
                if old_ntwk.graph.has_edge(source, target):
                    self.graph[source][target]["out_port"] = old_ntwk.graph[source][
                        target
                    ]["out_port"]
                    self.graph[source][target]["wire"] = old_ntwk.graph[source][target][
                        "wire"
                    ]
                    # No need to set wire out and switch out since the references are the same

        for source, s_info in self.get_leo_satellites():
            for target in list(self.graph.adj[source]):
                if not old_ntwk.graph.has_edge(source, target):
                    occupied_ports = {
                        self.graph[source][t]["out_port"]
                        for t in self.graph.adj[source]
                        if "out_port" in self.graph[source][t]
                    }
                    all_ports = set(range(len(list(self.graph.adj[source]))))
                    free_ports = all_ports - occupied_ports
                    new_port = next(iter(free_ports))
                    if new_port >= len(s_info["switch"].ports):
                        s_info["switch"].ports.append(
                            Port(env,
                            rate=8000,
                            qlimit=8000,
                            limit_bytes=False,
                            element_id=f"{source}_{new_port}",
                            debug=False)
                        )
                        s_info["switch"].demux = FIBDemux(fib=None, outs=s_info["switch"].ports, default=None)

                    delay_dist = self.graph[source][target]["length"] / (
                        constants.c / 1000
                    )

                    wire = Wire(
                        env,
                        delay_dist=lambda: delay_dist,
                    )

                    self.graph[source][target]["out_port"] = new_port
                    self.graph[source][target]["wire"] = wire
                    s_info["switch"].ports[new_port].out = wire

                    if self.graph.nodes[target]["type"] == NodeTypes.LEO_SATELLITE:
                        wire.out = self.graph.nodes[target]["switch"]
                    else:
                        wire.out = self.graph.nodes[target]["packet_sink"]

        # Upstream Link
        for gs, info in self.get_GSs():
            upstream_sat = next(iter(list(self.graph.adj[gs])))
            if old_ntwk.graph.has_edge(gs, upstream_sat):
                self.graph[gs][upstream_sat]["wire"] = old_ntwk.graph[gs][upstream_sat][
                    "wire"
                ]
            else:
                print(gs, upstream_sat)
                delay_dist = self.graph[gs][upstream_sat]["length"] / (
                    constants.c / 1000
                )
                for target, pg in info["packet_generator"].items():
                    wire = Wire(
                        env,
                        delay_dist=lambda: delay_dist,
                    )

                    if "wire" not in self.graph[gs][upstream_sat]:
                        self.graph[gs][upstream_sat]["wire"] = dict()
                    self.graph[gs][upstream_sat]["wire"][target] = wire

                    pg.out = wire
                    wire.out = self.graph.nodes[upstream_sat]["switch"]

        # Routing
        self.__set_up_sat_switches_for_routing()

        return self

    def __set_up_sat_switches_for_routing(self) -> None:
        for source, _ in self.get_GSs():
            for target, _ in self.get_GSs():
                if source == target:
                    continue

                sp, _ = self.get_shortest_path(source, target, "length")

                source, target, hops_but_first = sp[0], sp[-1], sp[1:]
                prev_hop = source

                for hop in hops_but_first:
                    if self.graph.nodes[prev_hop]["type"] != NodeTypes.GROUD_STATION:
                        if self.graph.nodes[prev_hop]["switch"].demux.fib == None:
                            self.graph.nodes[prev_hop]["switch"].demux.fib = dict()

                        self.graph.nodes[prev_hop]["switch"].demux.fib[
                            self.graph.nodes[source]["packet_generator"][target].flow_id
                        ] = self.graph[prev_hop][hop]["out_port"]

                    prev_hop = hop

    @classmethod
    def from_json(cls, env: simpy.Environment, file: Path) -> Self:
        with open(file, "r") as f:
            data = json.loads(f.read())

        nx_obj = data["networkx_obj"]

        ntwk = cls(graph=nx.DiGraph(nx.node_link_graph(nx_obj)))

        return ntwk.__build(env)

    @classmethod
    def from_topology_builder_svc(
        cls, env: simpy.Environment, svc_url: str, old_ntwk: Self = None
    ) -> Self:
        data = requests.get(url=svc_url).json()

        nx_obj = data["networkx_obj"]

        ntwk = cls(graph=nx.DiGraph(nx.node_link_graph(nx_obj)))

        if old_ntwk:
            return ntwk.__update(env, old_ntwk)
        return ntwk.__build(env)
