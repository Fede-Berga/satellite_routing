from enum import Enum
import json
from typing import Any, List, Self, Tuple
from pathlib import Path
import networkx as nx
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from ns.switch.switch import SimplePacketSwitch
from ns.port.wire import Wire
import simpy
from scipy import constants


class NodeTypes(str, Enum):
    GROUD_STATION = "GROUD_STATION"
    LEO_SATELLITE = "LEO_SATELLITE"

class Network:
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
    
    def __build(self, env: simpy.Environment, topo: Self) -> Tuple[simpy.Environment, Self]:
        topo.graph = nx.DiGraph(topo.graph)

        # Set sink
        for _, info in topo.get_GSs():
            info["packet_sink"] = PacketSink(env, debug=False)

        # Set packet generators
        for i, (gs, gs_info) in enumerate(topo.get_GSs()):
            for j, (target, _) in enumerate(topo.get_GSs()):
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
        for node, info in topo.get_leo_satellites():
            info["switch"] = SimplePacketSwitch(
                env=env,
                nports=topo.graph.degree[node],
                port_rate=8000,
                buffer_size=8000,
                element_id=node,
            )

        #  isl wire, downstream gsl wire
        for source, s_info in topo.get_leo_satellites():
            for i, target in enumerate(list(topo.graph.adj[source])):
                delay_dist = topo.graph[source][target]["length"] / (constants.c / 1000)

                wire = Wire(
                    env,
                    delay_dist=lambda: delay_dist,
                )

                topo.graph[source][target]["out_port"] = i
                topo.graph[source][target]["wire"] = wire
                s_info["switch"].ports[i].out = wire

                if topo.graph.nodes[target]["type"] == NodeTypes.LEO_SATELLITE:
                    wire.out = topo.graph.nodes[target]["switch"]
                else:
                    wire.out = topo.graph.nodes[target]["packet_sink"]

        for gs, info in topo.get_GSs():
            upstream_sat = next(iter(list(topo.graph.adj[gs])))
            delay_dist = topo.graph[gs][upstream_sat]["length"] / (constants.c / 1000)

            wire = Wire(
                env,
                delay_dist=lambda: delay_dist,
            )

            topo.graph[gs][upstream_sat]['wire'] = wire
            wire.out = upstream_sat

            for _, pg in info['packet_generator'].items():
                pg.out = topo.graph.nodes[upstream_sat]["switch"]
        
        # for sat, _ in topo.get_leo_satellites():
        #     print(topo.graph.nodes[sat]["switch"].demux.fib)
        
        for source, _ in topo.get_GSs():
            for target, _ in topo.get_GSs():
                if source == target:
                    continue

                #print(f"\n{source}-->{target}")

                sp, _ = topo.get_shortest_path(source, target, "length")

                #print(f"{sp}")

                source, target, hops_but_first = sp[0], sp[-1], sp[1:]
                prev_hop = source

                for hop in hops_but_first:
                    if topo.graph.nodes[prev_hop]["type"] == NodeTypes.GROUD_STATION:
                        # gs -> sat
                        #print(f"link : {prev_hop} --> {hop}")
                        _
                    else:
                        # sat -> sat
                        # or
                        # sat -> gs
                        if topo.graph.nodes[prev_hop]["switch"].demux.fib == None:
                            topo.graph.nodes[prev_hop]["switch"].demux.fib = dict()
                        
                        topo.graph.nodes[prev_hop]["switch"].demux.fib[
                                topo.graph.nodes[source]["packet_generator"][target].flow_id
                        ] = topo.graph[prev_hop][hop]['out_port']

                        #print(f"link : {prev_hop} -{topo.graph[prev_hop][hop]['out_port']}-> {hop}")
                    
                    prev_hop = hop
        """
        for sat, _ in topo.get_leo_satellites():
            if topo.graph.nodes[sat]["switch"].demux.fib:
                print(sat, topo.graph.nodes[sat]["switch"].demux.fib)
        """

        return env, topo
    
    @classmethod
    def from_json(cls, env: simpy.Environment, file: Path) -> Self:
        with open(file, "r") as f:
            data = json.loads(f.read())

        nx_obj = data["networkx_obj"]

        topo = cls(graph=nx.node_link_graph(nx_obj))

        return topo.__build(env, topo)

    @classmethod
    def from_topology_builder_svc(cls, env: simpy.Environment, svc_url: str) -> Self:
        return cls.from_json(env, '../../topology_builder/results/iridium_static_status.json')
