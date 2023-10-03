import json
from typing import List
from ns.packet.dist_generator import DistPacketGenerator
from ns.packet.sink import PacketSink


class GroundStation:
    def __init__(
        self,
        id: int | None = None,
        name: str | None = None,
        packet_sink: PacketSink | None = None,
        packet_generator: List[DistPacketGenerator] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.packet_sink = packet_sink
        if packet_generator:
            self.packet_generator = packet_generator
        else:
            self.packet_generator = list()

    def __str__(self) -> str:
        dict = {
            "id": self.id,
            "name": self.name,
            "packet_generators": [
                {"element_id": pg.element_id, "flow_id": pg.flow_id, 'out_set' : True if pg.out != None else False} for pg in self.packet_generator
            ],
            "packet_sink" : True if self.packet_sink else False
        }

        return json.dumps(dict, indent=4)

    def __repr__(self) -> str:
        return self.__str__()
