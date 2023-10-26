from datetime import datetime, timedelta
import json
import simpy
from sns.network import Network
from sns.leo_satellite import ForwardingStrategy, LeoSatellite
from typing import Any
from collections import defaultdict as dd


def run_sns_simulation(
    env: simpy.Environment,
    svc_url: str,
    start_time: datetime,
    end_time: datetime,
    snapshot_duration: timedelta,
    forwarding_strategy: ForwardingStrategy,
) -> Any:
    now = start_time
    old_ntwk = None
    average_buffer_occupation = dd(int)
    number_of_packets_dropped = dd(int)
    number_of_packets_dropped_for_rounting_issues = dd(int)
    number_of_packets_dropped_for_buffer_issues = dd(int)
    number_of_packets_delivered = dd(int)
    number_of_packets_sent = dd(int)

    while now <= end_time:
        print(f"\nBuilding topology at {now}")

        ntwk = Network.from_topology_builder_svc(
            env=env,
            svc_url=f"{svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&no_gs_s=7",
            old_ntwk=old_ntwk,
            packet_forwarding_strategy=forwarding_strategy,
        )

        env.run(until=((now - start_time) + snapshot_duration).seconds)

        for _, satellite_info in ntwk.get_leo_satellites():
            leo_satellite: LeoSatellite = satellite_info["leo_satellite"]

            average_buffer_occupation[(now - start_time).seconds] += sum(
                [int(port.byte_size / 1500) for port in leo_satellite.out_ports.values()]
            ) / len(leo_satellite.out_ports.values())
        average_buffer_occupation[(now - start_time).seconds] /= len(
            ntwk.get_leo_satellites()
        )

        number_of_packets_dropped_for_rounting_issues[(now - start_time).seconds] = sum(
            [
                sat_info["leo_satellite"].routing_issues_drops
                for _, sat_info in ntwk.get_leo_satellites()
            ]
        )

        number_of_packets_dropped_for_buffer_issues[(now - start_time).seconds] = sum(
            [
                sat_info["leo_satellite"].port_drop()
                for _, sat_info in ntwk.get_leo_satellites()
            ]
        )

        number_of_packets_dropped[(now - start_time).seconds] = (
            number_of_packets_dropped_for_rounting_issues[(now - start_time).seconds]
            + number_of_packets_dropped_for_buffer_issues[(now - start_time).seconds]
        )

        number_of_packets_delivered[(now - start_time).seconds] = sum(
            [
                sum(list(gs_info["packet_sink"].packets_received.values()))
                for _, gs_info in ntwk.get_GSs()
            ]
        )

        number_of_packets_sent[(now - start_time).seconds] = sum(
           [
               sum([pg.packets_sent for pg in gs_info["packet_generator"].values()])
               for _, gs_info in ntwk.get_GSs()
           ]
        )

        # print(json.dumps(average_buffer_occupation, indent=4))

        old_ntwk = ntwk

        now += snapshot_duration

    return (
        average_buffer_occupation,
        number_of_packets_dropped,
        number_of_packets_dropped_for_rounting_issues,
        number_of_packets_dropped_for_buffer_issues,
        number_of_packets_sent,
        number_of_packets_delivered,
    )
