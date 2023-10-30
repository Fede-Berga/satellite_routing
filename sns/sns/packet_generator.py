from ns.packet.packet import Packet
import simpy
import networkx as nx
from typing import Callable
from datetime import timedelta
import sns.sr_header_builder as snshb
import sns.network_parameters as snsnp


class PacketGenerator:
    def __init__(
        self,
        env: simpy.Environment,
        src: str,
        dst: str,
        graph: nx.digraph,
        arrival_dist: Callable,
        size_dist: Callable,
        initial_delay=0,
        finish=float("inf"),
        flow_id=0,
        rec_flow=False,
        debug=False,
    ):
        self.env = env
        self.arrival_dist = arrival_dist
        self.size_dist = size_dist
        self.initial_delay = initial_delay
        self.finish = finish
        self.src = src
        self.dst = dst
        self.graph = graph
        self.timeout_routing_update = 1 # seconds

        self.sr_header_builder = None
        self.last_timeout_routing_update = env.now
        self.out = None
        self.packets_sent = 0
        self.action = env.process(self.run())
        self.flow_id = flow_id
        self.rec_flow = rec_flow
        self.time_rec = []
        self.size_rec = []
        self.debug = debug
    
    def __update_routing_info(self) -> None:
       yield self.env.timeout(snsnp.NetworkParameters.LEO_GEO_GS_TD)
       self.sr_header_builder = snshb.SourceRoutingHeaderBuilder.instance(self.graph)

    def run(self):
        yield self.env.timeout(self.initial_delay)
        while self.env.now < self.finish:
            yield self.env.timeout(self.arrival_dist())

            self.packets_sent += 1

            if not self.sr_header_builder:
                self.sr_header_builder = snshb.SourceRoutingHeaderBuilder.instance(self.graph)

            packet = Packet(
                time=self.env.now,
                size=self.size_dist(),
                packet_id=self.packets_sent,
                src=self.src,
                dst=self.dst,
                payload=self.sr_header_builder.get_sr_header(
                    src_gs=self.src, dst_gs=self.dst
                ),
            )

            if self.env.now - self.last_timeout_routing_update > self.timeout_routing_update:
                self.env.process(self.__update_routing_info())
                self.last_timeout_routing_update = self.env.now 

            if self.rec_flow:
                self.time_rec.append(packet.time)
                self.size_rec.append(packet.size)

            if self.debug:
                print(
                    f"Sent packet {packet.packet_id} with src-dst {self.src}-{self.dst} at "
                    f"time {self.env.now}."
                )

            self.out.put(packet)
