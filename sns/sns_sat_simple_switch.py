import simpy
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from sns.sns.network import Topology, NodeTypes
from ns.switch.switch import SimplePacketSwitch
from ns.port.wire import Wire
from scipy import constants


def main():
    env = simpy.Environment()

    topo = Topology.from_json("../topology_builder/results/iridium_static_status.json")

    for _, info in topo.get_GSs():
        info["packet_sink"] = PacketSink(env, debug=False)

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

    for i, (gs, _) in enumerate(topo.get_GSs()):
        for j, (target, _) in enumerate(topo.get_GSs()):
            if gs == target:
                continue

            sp, _ = topo.get_shortest_path(gs, target, "length")

            print(f"\n{sp}")

            source, target, hops_but_first = sp[0], sp[-1], sp[1:]
            prev_hop = source

            for hop in hops_but_first:
                hop_info = topo.graph.nodes[hop]
                prev_hop_info = topo.graph.nodes[prev_hop]

                if "switch" not in hop_info:
                    hop_info["switch"] = SimplePacketSwitch(
                        env,
                        topo.graph.degree[hop],
                        port_rate=8000,
                        buffer_size=8000,
                        element_id=hop,
                    )

                delay_dist = topo.graph[prev_hop][hop]["length"] / (constants.c / 1000)

                wire = Wire(
                    env,
                    delay_dist=lambda: delay_dist,
                )

                if topo.graph.nodes[prev_hop]["type"] == NodeTypes.GROUD_STATION:
                    # curr -> sat
                    # prev --> gs
                    prev_hop_info["packet_generator"][target].out = wire
                    wire.out = hop_info["switch"]
                    print(f"link : {prev_hop} --> {hop}")
                else:
                    # curr -> sat
                    # prev -> sat
                    # or
                    # curr -> gs
                    # prev -> sat

                    index, forwarding_port = -1, None
                    for i, port in enumerate(
                        topo.graph.nodes[prev_hop]["switch"].ports
                    ):
                        if (
                            port.out != None
                            and port.out.out  # wire --> sat/gs
                            == topo.graph.nodes[hop][
                                "switch"
                                if topo.graph.nodes[hop]["type"]
                                == NodeTypes.LEO_SATELLITE
                                else "packet_sink"
                            ]
                        ):
                            index, forwarding_port = i, port
                            break

                    if forwarding_port == None:
                        for i, port in enumerate(
                            topo.graph.nodes[prev_hop]["switch"].ports
                        ):
                            if port.out == None:
                                index, forwarding_port = i, port
                                forwarding_port.out = wire
                                wire.out = topo.graph.nodes[hop][
                                    "switch"
                                    if topo.graph.nodes[hop]["type"]
                                    == NodeTypes.LEO_SATELLITE
                                    else "packet_sink"
                                ]
                                break

                    if topo.graph.nodes[prev_hop]["switch"].demux.fib == None:
                        topo.graph.nodes[prev_hop]["switch"].demux.fib = dict()

                    topo.graph.nodes[prev_hop]["switch"].demux.fib[
                        topo.graph.nodes[source]["packet_generator"][target].flow_id
                    ] = index

                    print(f"link : {prev_hop} --> {hop}")
                    print(f"forwarding port:index = {forwarding_port}:{index}")

                prev_hop = hop

    env.run(until=1000)

    for gs, info in topo.get_GSs():
        print(f"\n{gs}")
        for target, pg in info["packet_generator"].items():
            print(target, pg.element_id, pg.flow_id)
            print(f"sent : {pg.packets_sent}")
        print(f"received : {info['packet_sink'].packets_received}")


if __name__ == "__main__":
    main()
