from enum import Enum
import json
from typing import Any, List, Self, Tuple, Dict
import requests
import networkx as nx
from ns.packet.sink import PacketSink
from ns.port.wire import Wire
from ns.port.port import Port
import simpy
from scipy import constants
import sns.leo_satellite as snsleo
import sns.packet_generator as snspg
import sns.network_parameters as snsntwkparams


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

    def __build(
        self,
        env: simpy.Environment,
        traffic_matrix: Dict[str, Dict[str, float]],
        old_ntwk: Self | None = None,
        packet_forwarding_strategy: snsleo.ForwardingStrategy = snsleo.ForwardingStrategy.PORT_FORWARDING,
        debug: bool = False,
    ) -> Self:
        # Set sink
        for gs, gs_info in self.get_GSs():
            if old_ntwk:
                gs_info["packet_sink"] = old_ntwk.graph.nodes[gs]["packet_sink"]
            else:
                gs_info["packet_sink"] = PacketSink(env, debug=debug)

        # Set packet generators
        for src_gs, src_gs_info in self.get_GSs():
            for dst_gs, _ in self.get_GSs():
                if src_gs == dst_gs:
                    continue

                if "packet_generator" not in src_gs_info:
                    src_gs_info["packet_generator"] = dict()

                if old_ntwk:
                    pg: snspg.PacketGenerator = old_ntwk.graph.nodes[src_gs][
                        "packet_generator"
                    ][dst_gs]
                    pg.graph = self.graph

                else:
                    ad = snsntwkparams.NetworkParameters.PACKET_SIZE / traffic_matrix[src_gs][dst_gs]
                    pg = snspg.PacketGenerator(
                        env=env,
                        src=src_gs,
                        dst=dst_gs,
                        graph=self.graph,
                        arrival_dist=lambda: ad,
                        size_dist=lambda: snsntwkparams.NetworkParameters.PACKET_SIZE,
                        debug=debug,
                    )

                src_gs_info["packet_generator"][dst_gs] = pg

        # Set sat network object
        for satellite, satellite_info in self.get_leo_satellites():
            if old_ntwk:
                satellite_info["leo_satellite"] = old_ntwk.graph.nodes[satellite][
                    "leo_satellite"
                ]
            else:
                satellite_info["leo_satellite"] = snsleo.LeoSatellite(
                    env=env,
                    element_id=satellite,
                    packet_forwarding_strategy=packet_forwarding_strategy,
                    out_ports=dict(),
                    out_sat_or_gs=dict(),
                    link_switch_delay=dict(),
                )

        # isl wire, downstream gsl wire
        for src_satellite, satellite_info in self.get_leo_satellites():
            src_satellite_network_object: snsleo.LeoSatellite = satellite_info[
                "leo_satellite"
            ]

            for out_port_number, dst_satellite in enumerate(
                list(self.graph.adj[src_satellite])
            ):
                delay_dist = self.graph[src_satellite][dst_satellite]["length"] / (
                    constants.c / 1000
                )

                wire = Wire(
                    env,
                    delay_dist=lambda: delay_dist,
                )

                if old_ntwk:
                    src_satellite_network_object.out_sat_or_gs[
                        out_port_number
                    ] = dst_satellite

                    if out_port_number not in src_satellite_network_object.out_ports:
                        src_satellite_network_object.out_ports[out_port_number] = Port(
                            env=env,
                            rate=snsntwkparams.NetworkParameters.SATELLITE_PORT_RATE,
                            qlimit=snsntwkparams.NetworkParameters.SATELLITE_QUEUE_SIZE,
                            limit_bytes=snsntwkparams.NetworkParameters.LIMIT_BYTES,
                            debug=debug,
                        )

                        lsd = snsntwkparams.NetworkParameters.LINK_SWITCH_DELAY
                    else:
                        dst_ntwk_network_object = (
                            self.graph.nodes[dst_satellite]["leo_satellite"]
                            if self.graph.nodes[dst_satellite]["type"]
                            == NodeTypes.LEO_SATELLITE
                            else self.graph.nodes[dst_satellite]["packet_sink"]
                        )

                        lsd = (
                            0
                            if src_satellite_network_object.out_ports[
                                out_port_number
                            ].out.out
                            == dst_ntwk_network_object
                            else snsntwkparams.NetworkParameters.LINK_SWITCH_DELAY
                        )

                    src_satellite_network_object.link_switch_delay[
                        out_port_number
                    ] = lsd
                else:
                    src_satellite_network_object.out_ports[out_port_number] = Port(
                        env=env,
                        element_id=f"{src_satellite}->{dst_satellite}",
                        rate=snsntwkparams.NetworkParameters.SATELLITE_PORT_RATE,
                        qlimit=snsntwkparams.NetworkParameters.SATELLITE_QUEUE_SIZE,
                        limit_bytes=snsntwkparams.NetworkParameters.LIMIT_BYTES,
                        debug=debug,
                    )

                    src_satellite_network_object.out_sat_or_gs[
                        out_port_number
                    ] = dst_satellite

                    src_satellite_network_object.link_switch_delay[out_port_number] = 0

                src_satellite_network_object.out_ports[out_port_number].out = wire
                wire.out = (
                    self.graph.nodes[dst_satellite]["leo_satellite"]
                    if self.graph.nodes[dst_satellite]["type"]
                    == NodeTypes.LEO_SATELLITE
                    else self.graph.nodes[dst_satellite]["packet_sink"]
                )

        # gs --> sat links
        for src_gs, src_gs_info in self.get_GSs():
            upstream_sat = next(iter(list(self.graph.adj[src_gs])))

            delay_dist = self.graph[src_gs][upstream_sat]["length"] / (
                constants.c / 1000
            )

            wire = Wire(
                env,
                delay_dist=lambda: delay_dist,
            )

            for dst_satellite, pg in src_gs_info["packet_generator"].items():
                pg.out = wire
                wire.out = self.graph.nodes[upstream_sat]["leo_satellite"]

        return self

    def dump_status(self):
        # dump gs_s
        for source, info in self.get_GSs():
            print(f"{source}-sent")
            for target, pg in list(info["packet_generator"].items()):
                print(f"    │")
                print(
                    f"    ├ --flow : {pg.flow_id}-> {target}, packets sent : {pg.packets_sent}"
                )
            print(f"{source}-received")
            for flow_id, n_packets in list(
                info["packet_sink"].packets_received.items()
            ):
                print(f"    │")
                print(
                    f"    ├ --flow : {flow_id}-> {source}, packets received : {n_packets}"
                )

        # dump leo_sats
        print("\n")
        for sat, sat_info in self.get_leo_satellites():
            if sat_info["leo_satellite"].packets_received == 0:
                continue
            print(f"{sat}")
            print(f"    │")
            print(
                f"    │-total number of packets arrived: {sat_info['leo_satellite'].packets_received}"
            )
            print(
                f"    │-total number of packets sent: {sat_info['leo_satellite'].packets_sent()}"
            )
            print(
                f"    │-number of packets dropped for routing issues: {sat_info['leo_satellite'].routing_issues_drops}"
            )
            print(
                f"    │-number of packets dropped for port issues: {sat_info['leo_satellite'].port_drop()}"
            )
            if all(
                [
                    port.packets_received == 0
                    for port in sat_info["leo_satellite"].out_ports.values()
                ]
            ):
                continue
            for out_port_number, out_port in sat_info[
                "leo_satellite"
            ].out_ports.items():
                if out_port.packets_received == 0:
                    continue
                print(f"    │")
                print(f"    ├ -- out_port_number: {out_port_number} ")
                print(f"    ├ -- id: {out_port.element_id} ")
                print(f"    ├ -- packets_received: {out_port.packets_received}")
                print(
                    f"    ├ -- packets_sent: {out_port.packets_received - out_port.packets_dropped - int(out_port.byte_size / snsntwkparams.NetworkParameters.PACKET_SIZE)}"
                )
                print(f"    ├ -- packets_dropped: {out_port.packets_dropped}   ")
                print(
                    f"    ├ -- buffer size in bytes: {int(out_port.byte_size)}"
                )

    @classmethod
    def from_topology_builder_svc(
        cls,
        env: simpy.Environment,
        topology_builder_svc_url: str,
        traffic_matrix: Dict[str, Dict[str, float]],
        old_ntwk: Self = None,
        packet_forwarding_strategy: snsleo.ForwardingStrategy = snsleo.ForwardingStrategy.PORT_FORWARDING,
    ) -> Self:
        topology_builder_svc_data = requests.get(url=topology_builder_svc_url).json()

        nx_obj = topology_builder_svc_data["networkx_obj"]
        ntwk = cls(graph=nx.DiGraph(nx.node_link_graph(nx_obj)))

        return ntwk.__build(
            env=env,
            traffic_matrix=traffic_matrix,
            old_ntwk=old_ntwk,
            packet_forwarding_strategy=packet_forwarding_strategy,
        )
