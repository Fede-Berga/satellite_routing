import simpy
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from sns.topology import Topology

def main():
    env = simpy.Environment()

    topo = Topology.from_json("../topology_builder/results/iridium_static_status.json")

    for _, info in topo.get_GSs():
        info["packet_sink"] = PacketSink(env, debug=False)

    for i, (gs, gs_info) in enumerate(topo.get_GSs()):
        for j, (target, target_info) in enumerate(topo.get_GSs()):
            if gs == target:
                continue
                
            print(gs, target)

            pg = DistPacketGenerator(
                env,
                f"{gs.lower()}_to_{target.lower()}_pg",
                lambda: 1.5,
                lambda: 100.0,
                flow_id=int(str(i) + str(j)),
                debug=False
            )

            pg.out = target_info['packet_sink']

            if 'packet_generator' not in gs_info:
                gs_info['packet_generator'] = list()

            gs_info['packet_generator'].append(pg)

    env.run(until=100)

    for gs, info in topo.get_GSs():
        print(f"\n{gs}")
        for pg in info['packet_generator']:
            print(pg.element_id, pg.flow_id)
            print(f"sent : {pg.packets_sent}")
        print(f"received : {info['packet_sink'].packets_received}")

if __name__ == '__main__':
    main()