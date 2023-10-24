from typing import Dict
from ns.port.port import Port
from ns.packet.packet import Packet
import simpy


class LeoSatellite:
    def __init__(
        self,
        env: simpy.Environment,
        element_id: str,
        out_ports: Dict[int, Port],
        link_switch_delay: Dict[int, float],
        setup_delay: float = 0
    ) -> None:
        self.env = env
        self.element_id = element_id
        self.out_ports = out_ports
        self.setup_delay = setup_delay
        self.link_switch_delay = link_switch_delay
        self.action = env.process(self.run())
        self.store = simpy.Store(env)

        self.port_not_found_drops = 0  # total packet dropped
        self.packets_received = 0
    
    #def __str__(self) -> str:
    #    return f"Satellite {self.element_id}, ports {list(self.out_ports.keys())}"

    #def __repr__(self) -> str:
    #    return self.__str__()

    def packets_sent(self) -> int:
        return sum([port.packets_received - port.packets_dropped - int(port.byte_size / 1500) for port in self.out_ports.values()])
    
    def port_drop(self) -> int:
        return sum([port.packets_dropped for port in self.out_ports.values()])

    def run(self):
        yield self.env.timeout(self.setup_delay)
        while True:
            packet: Packet = yield self.store.get()
            header_out_port = packet.payload.pop() if packet.payload else None
            if header_out_port not in self.out_ports:
                self.port_not_found_drops += 1
            else:
                self.env.process(
                    self.process_packet(packet, port=header_out_port)
                )

    def process_packet(self, packet: Packet, port: int) -> None:
        if self.link_switch_delay[port] != 0 and self.env.now <= self.link_switch_delay[port]:
            print(
                f"waiting on port {port}, packet {packet.flow_id} for {self.link_switch_delay[port] - self.env.now}"
            )
            yield self.env.timeout(self.link_switch_delay[port] - self.env.now)
        self.out_ports[port].put(packet)

    def put(self, packet):
        self.packets_received += 1
        return self.store.put(packet)
