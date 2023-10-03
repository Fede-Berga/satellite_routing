import datetime
import pytz
from topology_builder.builder.topology_builder import MinimumDistanceTopologyBuilder
from topology_builder.topology.topology import Topology


class TestAddGroundStation:
    def test_add_gs(self):
        gs_s = [
            {"name": "Aberdeen", "lat": 57.9, "lon": 2.9},
            {"name": "Bombai", "lat": 19.0, "lon": 72.48},
        ]

        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_GSs(gs_s)
            .build()
        )

        # print(topology)

        assert len(topology.get_GSs()) == 2

    def test_add_gs_empty_list(self):
        topology: Topology = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name="Iridium",
                t=datetime.datetime(year=2023, month=9, day=12, tzinfo=pytz.UTC),
            )
            .add_GSs([])
            .build()
        )

        print(topology)

        assert len(topology.get_GSs()) == 0
