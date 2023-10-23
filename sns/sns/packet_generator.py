from ns.packet.packet import Packet
import simpy
from typing import Callable


class PacketGenerator:
    def __init__(
        self,
        env: simpy.Environment,
        src: str,
        dst: str,
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

        self.out = None
        self.packets_sent = 0
        self.action = env.process(self.run())
        self.flow_id = flow_id
        self.rec_flow = rec_flow
        self.time_rec = []
        self.size_rec = []
        self.debug = debug

    def run(self):
        """The generator function used in simulations."""
        yield self.env.timeout(self.initial_delay)
        while self.env.now < self.finish:
            # wait for next transmission
            yield self.env.timeout(self.arrival_dist())

            self.packets_sent += 1

            packet = Packet(
                time=self.env.now,
                size=self.size_dist(),
                packet_id=self.packets_sent,
                src=self.src,
                dst=self.dst,
                payload=list()
            )

            if self.rec_flow:
                self.time_rec.append(packet.time)
                self.size_rec.append(packet.size)

            if self.debug:
                print(
                    f"Sent packet {packet.packet_id} with src-dst {self.src}-{self.dst} at "
                    f"time {self.env.now}."
                )

            self.out.put(packet)
