from datetime import datetime, timedelta
import simpy
import pytz
import sys
import os
import matplotlib.pyplot as plt
import yaml

sys.path.append(os.path.abspath("../sns"))
from sns.sns import run_sns_simulation
from sns.leo_satellite import ForwardingStrategy
import sns.network_parameters as ntwkparams


if __name__ == "__main__":
    topology_builder_svc_url = (
        "http://localhost:8000/topology_builder/min_dist_topo_builder/iridium"
    )
    traffic_matrix_svc_url = (
        "http://localhost:8001/traffic_matrix"
    )
    start_time = datetime(
        year=2023, month=9, day=12, hour=10, minute=0, second=0, tzinfo=pytz.UTC
    )
    end_time = datetime(
        year=2023, month=9, day=12, hour=10, minute=10, second=0, tzinfo=pytz.UTC
    )
    snapshot_duration = timedelta(seconds=1)

    forwarding_strategies = [
        ForwardingStrategy.PORT_FORWARDING,
        ForwardingStrategy.EARLY_DISCARDING,
    ]

    analytics = dict()

    with open(ntwkparams.NetworkParameters.CITIES_FILE_PATH, "r") as cities_file:
        cities = yaml.load(cities_file, Loader=yaml.FullLoader)["cities"]

    for forwarding_strategy in forwarding_strategies:
        analytics[forwarding_strategy] = run_sns_simulation(
            env=simpy.Environment(),
            topology_builder_svc_url=topology_builder_svc_url,
            traffic_matrix_svc_url=traffic_matrix_svc_url,
            cities=cities,
            start_time=start_time,
            end_time=end_time,
            snapshot_duration=snapshot_duration,
            forwarding_strategy=forwarding_strategy,
        )

    for forwarding_strategy in forwarding_strategies:
        print(f"\n{str(forwarding_strategy)}")
        print(
            f"Total number of packets sent: {list(analytics[forwarding_strategy][4].values())[-1]}"
        )
        print(
            f"Total number of packets dropped: {list(analytics[forwarding_strategy][1].values())[-1]}"
        )
        print(
            f"Total number of packets delivered w.r.t. total number of packets sent: {list(analytics[forwarding_strategy][5].values())[-1] / list(analytics[forwarding_strategy][4].values())[-1]}"
        )
        print(
            f"Number of packets dropped for routing issues w.r.t. total number of packets dropped: {list(analytics[forwarding_strategy][2].values())[-1] / list(analytics[forwarding_strategy][1].values())[-1]}"
        )
        print(
            f"Number of packets dropped for routing issues w.r.t. total number of packets sent: {list(analytics[forwarding_strategy][2].values())[-1] / list(analytics[forwarding_strategy][4].values())[-1]}"
        )
        print(
            f"Number of packets dropped for buffer issues w.r.t. total number of packets dropped: {list(analytics[forwarding_strategy][3].values())[-1] / list(analytics[forwarding_strategy][1].values())[-1]}"
        )
        print(
            f"Number of packets dropped for buffer issues w.r.t. total number of packets sent: {list(analytics[forwarding_strategy][3].values())[-1] / list(analytics[forwarding_strategy][4].values())[-1]}"
        )

    """
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for forwarding_strategy in forwarding_strategies:
        buffer_occupation = analytics[forwarding_strategy][0]

        x_labels = buffer_occupation.keys()
        y_labels = buffer_occupation.values()

        plt.plot(
            x_labels,
            y_labels,
            label=str(forwarding_strategy),
        )

        # mean_duration = sum(y_labels) / len(y_labels)

        # plt.axhline(
        #     mean_duration,
        #     color=get_random_color(),
        #     linestyle="dashed",
        #     linewidth=1,
        #     label=f"{builder.__name__}, \nmean : {round(mean_duration, 2)} s",
        # )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time relative to the beginning")
    plt.ylabel("Average buffer occupation in bytes")
    title = f"Average buffer occupation in bytes through time of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/{'_'.join(title.lower().split())}")

    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for forwarding_strategy in forwarding_strategies:
        total_packet_drops = analytics[forwarding_strategy][1]

        x_labels = total_packet_drops.keys()
        y_labels = total_packet_drops.values()

        plt.plot(
            x_labels,
            y_labels,
            label=str(forwarding_strategy),
        )

        # mean_duration = sum(y_labels) / len(y_labels)

        # plt.axhline(
        #     mean_duration,
        #     color=get_random_color(),
        #     linestyle="dashed",
        #     linewidth=1,
        #     label=f"{builder.__name__}, \nmean : {round(mean_duration, 2)} s",
        # )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time relative to the beginning")
    plt.ylabel("Number of packets dropped")
    title = f"Number of packets dropped through time of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/{'_'.join(title.lower().split())}")

    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for forwarding_strategy in forwarding_strategies:
        packets_dropped_for_routing_issues = analytics[forwarding_strategy][2]

        x_labels = packets_dropped_for_routing_issues.keys()
        y_labels = packets_dropped_for_routing_issues.values()

        plt.plot(
            x_labels,
            y_labels,
            label=str(forwarding_strategy),
        )

        # mean_duration = sum(y_labels) / len(y_labels)

        # plt.axhline(
        #     mean_duration,
        #     color=get_random_color(),
        #     linestyle="dashed",
        #     linewidth=1,
        #     label=f"{builder.__name__}, \nmean : {round(mean_duration, 2)} s",
        # )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time relative to the beginning")
    plt.ylabel("Number of packets dropped for routing issues")
    title = f"Number of packets dropped for routing issues through time of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/{'_'.join(title.lower().split())}")

    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for forwarding_strategy in forwarding_strategies:
        packets_dropped_for_buffer_issues = analytics[forwarding_strategy][3]

        x_labels = packets_dropped_for_buffer_issues.keys()
        y_labels = packets_dropped_for_buffer_issues.values()

        plt.plot(
            x_labels,
            y_labels,
            label=str(forwarding_strategy),
        )

        # mean_duration = sum(y_labels) / len(y_labels)

        # plt.axhline(
        #     mean_duration,
        #     color=get_random_color(),
        #     linestyle="dashed",
        #     linewidth=1,
        #     label=f"{builder.__name__}, \nmean : {round(mean_duration, 2)} s",
        # )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time relative to the beginning")
    plt.ylabel("Number of packets dropped for buffer issues")
    title = f"Number of packets dropped for buffer issues through time of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
    plt.title(title)
    plt.savefig(f"images/{'_'.join(title.lower().split())}")
    
    for forwarding_strategy in forwarding_strategies:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        
        buffer_occupation, packets_dropped = analytics[forwarding_strategy][0], analytics[forwarding_strategy][1]

        for i, stats in enumerate([buffer_occupation, packets_dropped]):
            x_labels = stats.keys()
            y_labels = stats.values()

            plt.plot(
                x_labels,
                y_labels,
                label='Buffer occupation' if i == 0 else 'Packets dropped'
            )

        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("Time relative to the beginning")
        plt.ylabel("Number of packets")
        title = f"Number of packets dropped and buffer occupation using strategy {str(forwarding_strategy)} of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
        plt.title(title)
        plt.savefig(f"images/{'_'.join(title.lower().split())}")

    for forwarding_strategy in forwarding_strategies:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        
        packets_sent, packets_delivered = analytics[forwarding_strategy][4], analytics[forwarding_strategy][5]

        for i, stats in enumerate([packets_sent, packets_delivered]):
            x_labels = stats.keys()
            y_labels = stats.values()

            plt.plot(
                x_labels,
                y_labels,
                label='Packets sent' if i == 0 else 'Packets delivered'
            )

        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("Time relative to the beginning")
        plt.ylabel("Number of packets")
        title = f"Number of packets sent and delivered occupation using strategy {str(forwarding_strategy)} of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {(end_time - start_time).seconds} seconds."
        plt.title(title)
        plt.savefig(f"images/{'_'.join(title.lower().split())}")
        """
