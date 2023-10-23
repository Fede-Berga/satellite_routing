from datetime import datetime, timedelta

import simpy

from sns.network import Network
from sns.sr_header_builder import SourceRoutingHeaderBuilder


def run_sns_simulation(
    env: simpy.Environment,
    svc_url: str,
    start_time: datetime,
    end_time: datetime,
    snapshot_duration: timedelta,
) -> None:
    now = start_time
    old_ntwk = None

    while now <= end_time:
        print(f"Building topology at {now}")

        ntwk = Network.from_topology_builder_svc(
            env=env,
            svc_url=f"{svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&no_gs_s=4",
            old_ntwk=old_ntwk,
        )

        for src_gs, _ in ntwk.get_GSs():
            for dst_gs, _ in ntwk.get_GSs():
                if src_gs == dst_gs:
                    continue

                SourceRoutingHeaderBuilder.instance().get_route_list_of_ports(
                    src_gs=src_gs, dst_gs=dst_gs, ntwk=ntwk
                )

        return

        env.run(until=((now - start_time) + snapshot_duration).seconds)

        ntwk.dump_status()

        old_ntwk = ntwk

        now += snapshot_duration
