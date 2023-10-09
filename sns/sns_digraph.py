import itertools
import simpy
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from sns.sns.network import Topology, NodeTypes
from ns.switch.switch import SimplePacketSwitch
from ns.port.wire import Wire
from scipy import constants
import networkx as nx


def main():
    env = simpy.Environment()

    topo = Topology.from_json("../topology_builder/results/iridium_static_status.json")

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
    
    for sat, _ in topo.get_leo_satellites():
        print(topo.graph.nodes[sat]["switch"].demux.fib)
    
    for source, _ in topo.get_GSs():
        for target, _ in topo.get_GSs():
            if source == target:
                continue

            print(f"\n{source}-->{target}")

            sp, _ = topo.get_shortest_path(source, target, "length")

            print(f"{sp}")

            source, target, hops_but_first = sp[0], sp[-1], sp[1:]
            prev_hop = source

            for hop in hops_but_first:
                if topo.graph.nodes[prev_hop]["type"] == NodeTypes.GROUD_STATION:
                    # gs -> sat
                    print(f"link : {prev_hop} --> {hop}")
                else:
                    # sat -> sat
                    # or
                    # sat -> gs
                    if topo.graph.nodes[prev_hop]["switch"].demux.fib == None:
                        topo.graph.nodes[prev_hop]["switch"].demux.fib = dict()
                    
                    topo.graph.nodes[prev_hop]["switch"].demux.fib[
                            topo.graph.nodes[source]["packet_generator"][target].flow_id
                    ] = topo.graph[prev_hop][hop]['out_port']

                    print(f"link : {prev_hop} -{topo.graph[prev_hop][hop]['out_port']}-> {hop}")
                
                prev_hop = hop
    
    for sat, _ in topo.get_leo_satellites():
        if topo.graph.nodes[sat]["switch"].demux.fib:
            print(sat, topo.graph.nodes[sat]["switch"].demux.fib)

    env.run(until=100)

    for source, info in topo.get_GSs():
        for target, pg in info["packet_generator"].items():
            print(f"{source} -{pg.flow_id}-> {target}")
            print(f"sent : {pg.packets_sent}")
        print(f"received : {info['packet_sink'].packets_received}")


if __name__ == "__main__":
    main()
