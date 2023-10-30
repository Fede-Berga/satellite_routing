from datetime import datetime, timedelta
import json
import simpy
import sns.leo_satellite as snsleo
import sns.sr_header_builder as snssrb
import sns.packet_generator as snspg
import sns.network as snsntwk
import pytz


class TestSRHeaderBuilder:
    def test_srhb(self):
        env = simpy.Environment()
        svc_url = "http://localhost:8000/topology_builder/min_dist_topo_builder/iridium"
        start_time = datetime(
            year=2023, month=9, day=12, hour=10, minute=0, second=0, tzinfo=pytz.UTC
        )
        end_time = datetime(
            year=2023, month=9, day=12, hour=10, minute=0, second=3, tzinfo=pytz.UTC
        )
        snapshot_duration = timedelta(seconds=1)
        forwarding_strategy = snsleo.ForwardingStrategy.PORT_FORWARDING

        now = start_time
        old_ntwk = None

        print("\n")
        while now <= end_time:
            print(f"\nBuilding topology at {now}")

            ntwk = snsntwk.Network.from_topology_builder_svc(
                env=env,
                svc_url=f"{svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&no_gs_s=7",
                old_ntwk=old_ntwk,
                packet_forwarding_strategy=forwarding_strategy,
            )

            #env.run(until=((now - start_time) + snapshot_duration).seconds)

            for src_gs, _ in ntwk.get_GSs():
                for dst_gs, _ in ntwk.get_GSs():
                    if src_gs == dst_gs:
                        continue
                    print(
                        snssrb.SourceRoutingHeaderBuilder.instance(ntwk.graph).get_sr_header(
                            src_gs, dst_gs
                        )
                    )

            old_ntwk = ntwk

            now += snapshot_duration
