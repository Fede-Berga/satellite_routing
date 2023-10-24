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
        print(f"\nBuilding topology at {now}")

        ntwk = Network.from_topology_builder_svc(
            env=env,
            svc_url=f"{svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&no_gs_s=7",
            old_ntwk=old_ntwk,
        )

        env.run(until=((now - start_time) + snapshot_duration).seconds)

        ntwk.dump_status()

        old_ntwk = ntwk

        now += snapshot_duration
    
    total_routing_drop = sum([sum([pg.packets_sent for pg in gs_info['packet_generator'].values()]) for  _,  gs_info in ntwk.get_GSs()])

    print(f"total number of packets sent: {sum([sum([pg.packets_sent for pg in gs_info['packet_generator'].values()]) for  _,  gs_info in ntwk.get_GSs()])}") 
    print(f"total number of packets successfully delivered: {sum([sum(gs_info['packet_sink'].packets_received.values()) for  _,  gs_info in ntwk.get_GSs()])}")
    print(f"total number of packets dropped for routing issues: {sum([sat_info['leo_satellite'].port_not_found_drops for  _,  sat_info in ntwk.get_leo_satellites()])}")
    print(f"total number of packets dropped for port issues: {sum([sat_info['leo_satellite'].port_drop() for  _,  sat_info in ntwk.get_leo_satellites()])}")
