from datetime import datetime, timedelta
import json
import requests
import simpy
import yaml
import sns.leo_satellite as snsleo
import  sns.sr_header_builder as srhb
import sns.network as snsntwk
import sns.network_parameters as ntwkparams
import pytz


class TestSRHeaderBuilder:
    def test_srhb(self):
        env = simpy.Environment()

        topology_builder_svc_url = (
            "http://localhost:8000/topology_builder/min_dist_topo_builder/iridium"
        )

        traffic_matrix_svc_url = "http://localhost:8001/traffic_matrix"

        start_time = datetime(
            year=2023, month=9, day=12, hour=10, minute=0, second=0, tzinfo=pytz.UTC
        )

        end_time = datetime(
            year=2023, month=9, day=12, hour=10, minute=0, second=3, tzinfo=pytz.UTC
        )

        snapshot_duration = timedelta(seconds=1)

        forwarding_strategy = snsleo.ForwardingStrategy.PORT_FORWARDING

        with open("../../cities.yaml", "r") as cities_file:
            cities = yaml.load(cities_file, Loader=yaml.FullLoader)["cities"]

        now = start_time

        old_ntwk = None

        traffic_matrix = requests.get(
            url=f"{traffic_matrix_svc_url}?total_volume_of_traffic={ntwkparams.NetworkParameters.TOTAL_VOLUME_OF_TRAFFIC}&cities={','.join(cities)}",
        ).json()

        while now <= end_time:
            print(f"\nRunning simulation at {now}")

            ntwk = snsntwk.Network.from_topology_builder_svc(
                env=env,
                topology_builder_svc_url=f"{topology_builder_svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&cities={','.join(cities)}",
                traffic_matrix=traffic_matrix,
                old_ntwk=old_ntwk,
                packet_forwarding_strategy=forwarding_strategy,
                srhb_class=srhb.KShortestNodeDisjointSourceRoutingHeaderBuilder,
            )

            # env.run(until=((now - start_time) + snapshot_duration).seconds)

            for src_gs, _ in ntwk.get_GSs():
                for dst_gs, _ in ntwk.get_GSs():
                    if src_gs == dst_gs:
                        continue
                    print(
                        srhb.ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder.instance(
                            ntwk.graph
                        ).get_sr_header(
                            src_gs, dst_gs
                        )
                    )

            old_ntwk = ntwk

            now += snapshot_duration
