import json
from ns.switch.switch import SimplePacketSwitch


class LeoSatellite:
    def __init__(
        self,
        id: int | None = None,
        name: str | None = None,
        switch: SimplePacketSwitch | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.switch = switch

    def __str__(self) -> str:
        dict = {
            "id": self.id,
            "name": self.name,
            "switch": True if self.switch else False,
        }

        return json.dumps(dict, indent=4)

    def __repr__(self) -> str:
        return self.__str__()
