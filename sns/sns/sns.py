from datetime import datetime, timedelta
import simpy
from sns.network import Network
from sns.leo_satellite import ForwardingStrategy, LeoSatellite
import sns.network_parameters as ntwkparams
from typing import Any, List, Union
from collections import defaultdict as dd
import requests
import time
import sns.sr_header_builder as srhb

def run_sns_simulation(
    env: simpy.Environment,
    topology_builder_svc_url: str,
    traffic_matrix_svc_url: str,
    cities: List[str],
    start_time: datetime,
    end_time: datetime,
    snapshot_duration: timedelta,
    forwarding_strategy: ForwardingStrategy,
    srhb_class: Union[
        srhb.BaselineSourceRoutingHeaderBuilder,
        srhb.NoSmoothingOnBufferSizeSourceRoutingHeaderBuilder,
        srhb.ExponentialSmoothingOnBufferSizeSourceRoutingHeaderBuilder,
        srhb.KShortestNodeDisjointSourceRoutingHeaderBuilder,
    ] = srhb.BaselineSourceRoutingHeaderBuilder,
) -> Any:
    now = start_time
    old_ntwk = None

    average_buffer_occupation = dd(int)
    number_of_packets_dropped = dd(int)
    number_of_packets_dropped_for_rounting_issues = dd(int)
    number_of_packets_dropped_for_buffer_issues = dd(int)
    number_of_packets_delivered = dd(int)
    number_of_packets_sent = dd(int)

    traffic_matrix = requests.get(
        url=f"{traffic_matrix_svc_url}?total_volume_of_traffic={ntwkparams.NetworkParameters.TOTAL_VOLUME_OF_TRAFFIC}&cities={','.join(cities)}",
    ).json()

    while now <= end_time:
        print(f"\nRunning simulation at {now}")

        s_time = time.time()

        ntwk = Network.from_topology_builder_svc(
            env=env,
            topology_builder_svc_url=f"{topology_builder_svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&cities={','.join(cities)}",
            traffic_matrix=traffic_matrix,
            old_ntwk=old_ntwk,
            packet_forwarding_strategy=forwarding_strategy,
            srhb_class=srhb_class
        )

        print("--- Building took %s seconds ---" % (time.time() - s_time))
        
        env.run(until=((now - start_time) + snapshot_duration).seconds)

        print("--- Simulating took %s seconds ---" % (time.time() - s_time))

        #ntwk.dump_status()
        
        for _, satellite_info in ntwk.get_leo_satellites():
            leo_satellite: LeoSatellite = satellite_info["leo_satellite"]

            average_buffer_occupation[(now - start_time).seconds] += sum(
                [
                    int(port.byte_size / ntwkparams.NetworkParameters.PACKET_SIZE)
                    for port in leo_satellite.out_ports.values()
                ]
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
