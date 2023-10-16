from collections import defaultdict as dd
import datetime
from itertools import cycle
import os
from pathlib import Path
import random
import sys
import yaml
import json
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

sys.path.append(os.path.abspath("../topology_builder"))
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository
from topology_builder.builder.min_distance_topology_builder import (
    MinimumDistanceTopologyBuilder,
)
from topology_builder.builder.los_topology_builder import LOSTopologyBuilder


def fetch_simulation_parameters(config_file: str):
    with open(config_file, "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)

    dt = config["dt"]

    start_time = datetime.datetime.strptime(
        config["start_time"], "%Y-%m-%d %H:%M:%S %z"
    )

    end_time = datetime.datetime.strptime(config["end_time"], "%Y-%m-%d %H:%M:%S %z")

    gs_s = config["ground_stations"]

    constellation_path = config["constellation_file"]

    name = config["name"]

    return name, start_time, end_time, dt, constellation_path, gs_s


def collect_sp_analitics(
    builder_cls: type[LOSTopologyBuilder | MinimumDistanceTopologyBuilder],
):
    (
        name,
        start_time,
        end_time,
        dt,
        constellation_file,
        gs_s,
    ) = fetch_simulation_parameters("./config.yaml")

    now = start_time

    current_topology = (
        MinimumDistanceTopologyBuilder(verbose=False, name=name, t=now)
        .add_LEO_constellation(STKLeoSatelliteRepository(Path(constellation_file)))
        .add_ISLs()
        .add_GSs(gs_s)
        .add_GSLs()
        .build()
    )

    now += datetime.timedelta(milliseconds=dt)

    topology_stability_analitics = dd(int, {0: 1})
    average_link_length = {
        (now - start_time).seconds: sum(
            info["length"] for _, _, info in list(current_topology.ntwk.edges(data=True))
        )
        / len(list(current_topology.ntwk.edges))
    }
    link_changes = {
        (now - start_time).seconds: 0
    }

    while now <= end_time:
        previous_topology = current_topology

        print(f"Building topology at {now}")

        if builder_cls == LOSTopologyBuilder:
            current_topology = (
                builder_cls(
                    verbose=False, name=name, t=now, previous_topology=previous_topology
                )
                .add_LEO_constellation(
                    STKLeoSatelliteRepository(Path(constellation_file))
                )
                .add_ISLs()
                .add_GSs(gs_s)
                .add_GSLs()
                .build()
            )
        else:
            current_topology = (
                builder_cls(verbose=False, name=name, t=now)
                .add_LEO_constellation(
                    STKLeoSatelliteRepository(Path(constellation_file))
                )
                .add_ISLs()
                .add_GSs(gs_s)
                .add_GSLs()
                .build()
            )

        average_link_length[(now - start_time).seconds] = sum(
            info["length"] for _, _, info in list(current_topology.ntwk.edges(data=True))
        ) / len(list(current_topology.ntwk.edges))

        if not current_topology.is_different(previous_topology):
            topology_stability_analitics[(now - start_time).seconds] += 1
        else:
            topology_stability_analitics[list(topology_stability_analitics)[-1]] += 1
        
        link_changes[(now - start_time).seconds] = len(list(current_topology.get_diff_graph(previous_topology).edges))

        now = now + datetime.timedelta(milliseconds=dt)

    return topology_stability_analitics, average_link_length, link_changes


def get_random_color() -> cycle:
    colors = list(mcolors.CSS4_COLORS.items())
    random.shuffle(colors)
    colors = dict(colors)
    return next(cycle(colors))

if __name__ == "__main__":
    _, start_time, end_time, _, _, _ = fetch_simulation_parameters("./config.yaml")

    builders = [MinimumDistanceTopologyBuilder, LOSTopologyBuilder]
    analitics = dict()
    sim_duration = (end_time - start_time).seconds

    for builder in builders:
        analitics[builder.__name__] = collect_sp_analitics(builder)
    
    # Topology Stability Through time
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        stability_analitics, _, _ = analitics[builder.__name__]

        x_labels = stability_analitics.keys()
        y_labels = stability_analitics.values()

        plt.plot(
            x_labels,
            y_labels,
            # "-o",
            label=builder.__name__,
        )

        mean_duration = sum(y_labels) / len(y_labels)

        plt.axhline(
            mean_duration,
            color=get_random_color(),
            linestyle="dashed",
            linewidth=1,
            label=f"{builder.__name__}, \nmean : {round(mean_duration, 2)} s",
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("time relative to the beginning")
    plt.ylabel("Stability interval in seconds of the topology built in time t")
    title = f"Stability intervals in seconds through time of Iridium NEXT in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    plt.savefig(f"images/stability/{'_'.join(title.lower().split())}")
    #plt.show()

    # plot stability Frequences
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        stability_analitics, _, _ = analitics[builder.__name__]

        labels = [duration for duration in stability_analitics.values()]

        plt.hist(
            labels,
            alpha=0.5,
            label=builder.__name__,
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Duration of toplogies in seconds")
    plt.ylabel("Frequeces")
    title = f"Frequences of stability intervals of a topology in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    plt.savefig(f"images/stability/{'_'.join(title.lower().split())}")
    #plt.show()
    
    # Average link length through time
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        _, average_link_length, _ = analitics[builder.__name__]
        x_labels = average_link_length.keys()
        y_labels = average_link_length.values()

        plt.plot(
            x_labels,
            y_labels,
            # "-o",
            label=builder.__name__,
        )

        mean_link_len = sum(y_labels) / len(y_labels)

        plt.axhline(
            mean_link_len,
            color=get_random_color(),
            linestyle="dashed",
            linewidth=1,
            label=f"{builder.__name__}, \nmean : {round(mean_link_len, 2)} s",
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time of a topology relative to the beginning")
    plt.ylabel("Average link length in km of the topology at time t")
    title = f"Average link length in km of a topology in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/avg_link_len/{'_'.join(title.lower().split())}")

    # Frequences of link length through time
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        _, average_link_length, _ = analitics[builder.__name__]
        
        labels = [avg_len for avg_len in average_link_length.values()]

        plt.hist(
            labels,
            alpha=0.5,
            label=builder.__name__,
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Average link length in km")
    plt.ylabel("Frequences")
    title = f"Frequences of sverage link length in km of the topologies built in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/avg_link_len/{'_'.join(title.lower().split())}")

    # Link Change through time
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        _, _, link_changes = analitics[builder.__name__]
        x_labels = link_changes.keys()
        y_labels = link_changes.values()

        plt.plot(
            x_labels,
            y_labels,
            # "-o",
            label=builder.__name__,
        )

        avg_link_changes = sum(y_labels) / len(y_labels)

        plt.axhline(
            avg_link_changes,
            color=get_random_color(),
            linestyle="dashed",
            linewidth=1,
            label=f"{builder.__name__}, \nmean : {round(avg_link_changes, 2)} links",
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Time of a topology relative to the beginning")
    plt.ylabel("Number of link at time t changes w.r.t. the previous topology")
    title = f"Number of link at time t changes w.r.t. the previous topology in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/link_change/{'_'.join(title.lower().split())}")

    # Frequences of Link Change
    plt.figure(figsize=(15, 8))
    ax = plt.subplot()
    for builder in builders:
        _, _, link_changes = analitics[builder.__name__]

        labels = [n_changes for n_changes in link_changes.values()]

        plt.hist(
            labels,
            alpha=0.5,
            label=builder.__name__,
        )
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    plt.xlabel("Number of changes w.r.t. the previous topology")
    plt.ylabel("Frequences")
    title = f"Frequences of number of changes in a simulation \nstarted at {start_time}, lasted {sim_duration} seconds."
    plt.title(title)
    #plt.show()
    plt.savefig(f"images/link_change/{'_'.join(title.lower().split())}")