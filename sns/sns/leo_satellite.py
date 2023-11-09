from enum import Enum
from typing import Dict
from ns.port.port import Port
from ns.packet.packet import Packet
import simpy


class ForwardingStrategy(str, Enum):
    EARLY_DISCARDING = "EARLY_DISCARDING"
    PORT_FORWARDING = "PORT_FORWARDING"


class LeoSatellite:
    def __init__(
        self,
        env: simpy.Environment,
        element_id: str,
        packet_forwarding_strategy: ForwardingStrategy,
        out_ports: Dict[int, Port],
        out_sat_or_gs: Dict[int, str],
        link_switch_delay: Dict[int, float],
        setup_delay: float = 0,
    ) -> None:
        self.env = env
        self.element_id = element_id
        self.out_ports = out_ports
        self.out_sat_or_gs = out_sat_or_gs
        self.packet_forwarding_strategy = packet_forwarding_strategy
        self.setup_delay = setup_delay
        self.link_switch_delay = link_switch_delay
        self.action = env.process(self.run())
        self.store = simpy.Store(env)

        self.routing_issues_drops = 0  # total packet dropped
        self.packets_received = 0

    def packets_sent(self) -> int:
        return sum(
            [
                port.packets_received
                - port.packets_dropped
                - int(port.byte_size / 1500)
                for port in self.out_ports.values()
            ]
        )

    def port_drop(self) -> int:
        return sum([port.packets_dropped for port in self.out_ports.values()])

    def run(self):
        yield self.env.timeout(self.setup_delay)
        while True:
            packet: Packet = yield self.store.get()
            header_out_port, header_out_satellite_or_gs = (
                packet.payload.pop() if packet.payload else (None, None)
            )

            if (header_out_port, header_out_satellite_or_gs) != (None, None):
                if (
                    self.packet_forwarding_strategy
                    == ForwardingStrategy.PORT_FORWARDING
                ):
                    if header_out_port in self.out_ports:
                        link_setup_time = 0
                        if self.link_switch_delay[header_out_port] != 0:
                            link_setup_time = self.link_switch_delay[header_out_port]
                            self.link_switch_delay[header_out_port] = 0
                        self.env.process(
                            self.process_packet(
                                packet,
                                port=header_out_port,
                                link_setup_time=link_setup_time,
                            )
                        )
                    else:
                        self.routing_issues_drops += 1
                else:
                    if header_out_satellite_or_gs in self.out_sat_or_gs.values():
                        link_setup_time = 0
                        if self.link_switch_delay[header_out_port] != 0:
                            link_setup_time = self.link_switch_delay[header_out_port]
                            self.link_switch_delay[header_out_port] = 0
                        self.env.process(
                            self.process_packet(
                                packet,
                                port=header_out_port,
                                link_setup_time=link_setup_time,
                            )
                        )
                    else:
                        self.routing_issues_drops += 1
            else:
                self.routing_issues_drops += 1

    def process_packet(self, packet: Packet, port: int, link_setup_time: float) -> None:
        if link_setup_time != 0:
            print(
                f"{self.element_id}: waiting on port {port}, packet {packet.flow_id} for {link_setup_time}"
            )
            yield self.env.timeout(link_setup_time)
        self.out_ports[port].put(packet)

    def put(self, packet):
        self.packets_received += 1
        return self.store.put(packet)
