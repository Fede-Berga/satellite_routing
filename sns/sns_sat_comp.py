import copy
from datetime import datetime
import itertools
import simpy
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink
from sns.network import Network, NodeTypes
from ns.switch.switch import SimplePacketSwitch
from ns.port.wire import Wire
from sns.leo_satellite import LeoSatellite
from sns.packet_generator import PacketGenerator

if __name__ == "__main__":
    env = simpy.Environment()

    pg_1 = PacketGenerator(
        env=env,
        src="Mirabilandia",
        dst="Guala Lampur",
        arrival_dist=lambda: 1.5,
        size_dist=lambda: 100.0,
        debug=True,
    )

    ps_1 = PacketSink(env=env, debug=True)
    """
    sat = LeoSatellite(
        env=env,
        out_ports={
            0: _,
            1: _,
            2: _,
            3: _,

        },
        setup_delay=0,
        link_switch_delay={0: 2, 1: 0, 2: 2, 3: 0}
    )
    """
    pg_1.out = ps_1

    env.run(20)
