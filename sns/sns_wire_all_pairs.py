"""
An very simple example of using the test the packet drop in FairPacketSwitch.
It shows a bug in packet dropping process.
"""

import simpy
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from sns.topology import Topology
from ns.port.wire import Wire

env = simpy.Environment()

topo = Topology.from_json("iridium_2023-09-01 10:00:00+00:00.json")

for gs in topo.all_gs:
    gs.packet_sink = PacketSink(env, debug=True)

for i, gs in enumerate(topo.all_gs):
    for j, target in enumerate(topo.all_gs):
        if gs.id == target.id:
            continue

        pg = DistPacketGenerator(
            env,
            f"{gs.name.lower()}_to_{target.name.lower()}_pg",
            lambda: 1.5,
            lambda: 100.0,
            flow_id=int(str(i) + str(j)),
            debug=False
        )

        wire = Wire(
            env,
            delay_dist=lambda: 10
        )

        pg.out = wire
        wire.out = target.packet_sink

        gs.packet_generator.append(pg)

print(topo)

env.run(until=100)

for gs in topo.all_gs:
    print(f"\n{gs.name}")
    for pg in gs.packet_generator:
        print(pg.element_id, pg.flow_id)
        print(f"sent : {pg.packets_sent}")
    print(f"received : {gs.packet_sink.packets_received}")