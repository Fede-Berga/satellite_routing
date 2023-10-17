import copy
from enum import Enum
import json
import sys
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
import matplotlib.pyplot as plt


class NodeTypes(str, Enum):
    GROUD_STATION = "GROUD_STATION"
    LEO_SATELLITE = "LEO_SATELLITE"


ARRIVAL_DIST = 0.010  # seconds
SIZE_DIST = 1_500  # bytes
SATELLITE_SWITCH_PORT_RATE = 10_000_000  # bytes/s
SATELLITE_SWITCH_BUFFER_SIZE = 100  # Packets


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
                    lambda: ARRIVAL_DIST,
                    lambda: SIZE_DIST,
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
                port_rate=SATELLITE_SWITCH_PORT_RATE,
                buffer_size=SATELLITE_SWITCH_BUFFER_SIZE,
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
                            Port(
                                env,
                                rate=SATELLITE_SWITCH_PORT_RATE,
                                qlimit=SATELLITE_SWITCH_BUFFER_SIZE,
                                limit_bytes=False,
                                element_id=f"{source}_{new_port}",
                                debug=False,
                            )
                        )
                        s_info["switch"].demux = FIBDemux(
                            fib=None, outs=s_info["switch"].ports, default=None
                        )

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

    def dump_status(self):
        # dump gs_s
        for source, info in self.get_GSs():
            print(f"{source}-sent")
            for target, pg in list(info["packet_generator"].items())[:-1]:
                print(f"    │")
                print(
                    f"    ├ --flow : {pg.flow_id}-> {target}, packets sent : {pg.packets_sent}"
                )
            target, pg = list(info["packet_generator"].items())[-1]
            print(f"    │")
            print(
                f"    └ --flow : {pg.flow_id}-> {target}, packets sent : {pg.packets_sent}"
            )
            print(f"{source}-received")
            for flow_id, n_packets in list(
                info["packet_sink"].packets_received.items()
            )[:-1]:
                print(f"    │")
                print(
                    f"    ├ --flow : {flow_id}-> {source}, packets received : {n_packets}"
                )
            if len(list(info["packet_sink"].packets_received.items())) <= 1:
                continue
            flow_id, n_packets in list(info["packet_sink"].packets_received.items())[-1]
            print(f"    │")
            print(f"    └ --flow : {flow_id}, packets received : {n_packets}")

        # dump leo_sats
        print("\n")
        for sat, sat_info in self.get_leo_satellites():
            if all([port.packets_received == 0 for port in sat_info["switch"].ports]):
                continue
            print(
                f"\n{sat}, total number of packets arrived: {sat_info['switch'].demux.packets_received}"
            )
            for i, port in enumerate(sat_info["switch"].ports):
                if port.packets_received == 0:
                    continue
                target = None
                for adj, adj_info in self.graph.adj[sat].items():
                    if adj_info["out_port"] == i:
                        target = adj
                        break
                print(f"    │")
                print(f"    ├ -- out_port: {i}                             ")
                print(f"    ├ -- packets_received: {port.packets_received}     ")
                print(
                    f"    ├ -- packets_sent: {port.packets_received - port.packets_dropped - int(port.byte_size / SIZE_DIST)}     "
                )
                print(f"    ├ -- packets_dropped: {port.packets_dropped}   ")
                print(
                    f"    ├ -- buffer size in packets: {int(port.byte_size / SIZE_DIST)}    "
                )
                print(f"    ├ -- flows on this port")
                for flow_id, out_port in sat_info["switch"].demux.fib.items():
                    if out_port != i:
                        continue

                    s, t = None, None
                    for u, info in self.get_GSs():
                        for v, pg in list(info["packet_generator"].items()):
                            if pg.flow_id == flow_id:
                                s, t = u, v
                                break
                        if s != None and t != None:
                            break
                    print(f"        ├ -- flow: {s} --{flow_id}--> {t}")
                print(f"    ├ --> {target}")

    def dump_routing_info(self) -> None:
        for source, info in self.get_GSs():
            print(f"{source}")
            for target, pg in list(info["packet_generator"].items())[:-1]:
                print(f"    │")
                print(f"    ├ --flow : {pg.flow_id}-> {target}")
            target, pg = list(info["packet_generator"].items())[-1]
            print(f"    │")
            print(f"    └ --flow : {pg.flow_id}-> {target}")
        print("\n")
        for sat, sat_info in self.get_leo_satellites():
            if sat_info["switch"].demux.fib == None:
                continue
            print(f"{sat}")
            for flow, port in sat_info["switch"].demux.fib.items():
                target = None
                for v, edge_info in self.graph.adj[sat].items():
                    if edge_info["out_port"] == port:
                        target = v
                        break

                print(f"    │")
                print(f"    ├ --port : {port}, flow : {flow} --> {target}")

    def nx_plot(self) -> None:
        G = self.graph.copy()

        G.remove_nodes_from(
            [
                sat
                for sat, sat_info in self.get_leo_satellites()
                if sat_info["switch"].demux.fib == None
            ]
        )

        edges_to_remove = []
        for node, n_d in G.nodes(data=True):
            if n_d["type"] == NodeTypes.GROUD_STATION:
                for u, v in G.edges(node):
                    edges_to_remove.append((u, v))
                continue
            for u, v, d in G.edges(node, data=True):
                if d["out_port"] not in n_d["switch"].demux.fib.values():
                    edges_to_remove.append((u, v))
                else:
                    new_info = {
                        (u, v): {
                            "out_port": d["out_port"],
                            "flows": [
                                flow
                                for flow, port in n_d["switch"].demux.fib.items()
                                if port == d["out_port"]
                            ],
                        }
                    }
                    d.clear()
                    nx.set_edge_attributes(G, new_info)

        G.remove_edges_from(edges_to_remove)

        edge_port = dict(
            [((n1, n2), d["out_port"]) for n1, n2, d in G.edges(data=True)]
        )

        node_name = dict(
            [
                (n, n[-2:]) if d["type"] == NodeTypes.LEO_SATELLITE else (n, n[:2])
                for n, d in G.nodes(data=True)
            ]
        )
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=4, iterations=500)
        nx.draw_networkx_nodes(G, pos, node_size=500)
        nx.draw_networkx_edges(G, pos, connectionstyle="arc3, rad = 0.2")
        nx.draw_networkx_labels(G, pos, labels=node_name)
        plt.show()

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
