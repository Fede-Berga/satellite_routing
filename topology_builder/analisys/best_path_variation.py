import random
import matplotlib.colors as mcolors
import datetime
from itertools import combinations, cycle
from pathlib import Path
import yaml
import networkx as nx
import matplotlib.pyplot as plt
import sys
import os
from mdutils.mdutils import MdUtils

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
    hopcount: bool = False,
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
    shortest_path_analitics = dict()

    current_topology = (
        MinimumDistanceTopologyBuilder(verbose=False, name=name, t=now)
        .add_LEO_constellation(STKLeoSatelliteRepository(Path(constellation_file)))
        .add_ISLs()
        .add_GSs(gs_s)
        .add_GSLs()
        .build()
    )

    now += datetime.timedelta(milliseconds=dt)

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

        s_t_couples = list(combinations(current_topology.get_GSs(), 2))

        for s, t in s_t_couples:
            p = nx.shortest_path(
                G=current_topology.ntwk,
                source=s,
                target=t,
                weight=None if hopcount else "length",
            )

            if s not in shortest_path_analitics.keys():
                shortest_path_analitics[s] = dict()

            if t not in shortest_path_analitics[s].keys():
                shortest_path_analitics[s][t] = dict()

            if str(p) not in shortest_path_analitics[s][t].keys():
                shortest_path_analitics[s][t][str(p)] = {
                    "len_hops": nx.shortest_path_length(
                        G=current_topology.ntwk, source=s, target=t
                    ),
                    "len_km": nx.shortest_path_length(
                        G=current_topology.ntwk, source=s, target=t, weight="length"
                    ),
                    "duration": 0,
                }
            else:
                shortest_path_analitics[s][t][str(p)]["duration"] += 1

            # print(json.dumps(shortest_path_analitics, indent=4))

        now = now + datetime.timedelta(milliseconds=dt)

    return shortest_path_analitics


def get_shuffled_matplotlib_colors() -> cycle:
    colors = list(mcolors.CSS4_COLORS.items())
    random.shuffle(colors)
    colors = dict(colors)
    return cycle(colors)


def plot_average_duration_of_sp(
    builder: type[LOSTopologyBuilder | MinimumDistanceTopologyBuilder],
    shortest_path_analitics,
    sim_duration,
    hopcount: bool = False,
):
    x_labels = list(combinations(shortest_path_analitics.keys(), 2))
    y_labels = [
        sim_duration / len(shortest_path_analitics[s][t].keys()) for s, t in x_labels
    ]

    plt.plot(
        range(len(x_labels)),
        y_labels,
        "-o",
        label=f"{builder.__name__}, {'hopcount' if hopcount else 'distance'}",
    )

    mean_path_duration = sum(y_labels) / len(y_labels)

    plt.axhline(
        mean_path_duration,
        color=next(get_shuffled_matplotlib_colors()),
        linestyle="dashed",
        linewidth=1,
        label=f"Builder: {builder.__name__}, \nmetric: {'hopcount' if hopcount else 'distance'}, \nmean : {round(mean_path_duration, 2)} s",
    )


def plot_average_distance_of_sp(
    builder: type[LOSTopologyBuilder | MinimumDistanceTopologyBuilder],
    shortest_path_analitics,
    hopcount: bool = False,
):
    x_labels = list(combinations(shortest_path_analitics.keys(), 2))
    y_labels = [
        sum(
            shortest_path_analitics[s][t][path]["len_hops" if hopcount else "len_km"]
            for path in shortest_path_analitics[s][t].keys()
        )
        / len(shortest_path_analitics[s][t].keys())
        for s, t in x_labels
    ]

    plt.plot(
        range(len(x_labels)),
        y_labels,
        "-o",
        label=f"{builder.__name__}, {'hopcount' if hopcount else 'distance'}",
    )

    mean_path_dist = sum(y_labels) / len(y_labels)

    plt.axhline(
        mean_path_dist,
        color=next(get_shuffled_matplotlib_colors()),
        linestyle="dashed",
        linewidth=1,
        label=f"{builder.__name__}, \nmean : {round(mean_path_dist, 2)} {'hops' if hopcount else 'km'}",
    )


if __name__ == "__main__":
    _, start_time, end_time, _, _, gs_s = fetch_simulation_parameters("./config.yaml")

    mdFile = MdUtils(file_name='s_t_couple_index',title='Ground Station Index-Couple')
    list_of_strings = ["Index", "s", "t"]
    for i, (s, t) in enumerate(list(combinations(gs_s, 2))):
        list_of_strings.extend([i, s['name'], t['name']])
    mdFile.new_table(columns=3, rows=len(list(combinations(gs_s, 2))) + 1, text=list_of_strings, text_align='center')
    mdFile.create_md_file()

    builders = [LOSTopologyBuilder, MinimumDistanceTopologyBuilder]
    shortest_path_analitics = dict()
    sim_duration = (end_time - start_time).seconds

    # Collect Analitics
    for builder in builders:
        shortest_path_analitics[str(builder)] = dict()
        for hopcount in [True, False]:
            shortest_path_analitics[str(builder)][hopcount] = collect_sp_analitics(
                builder, hopcount=hopcount
            )

    # -------------------------------------------
    # Average Duration same builder different metric

    # Plot average duration of sp with length metric
    for builder in builders:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        for hopcount in [True, False]:
            plot_average_duration_of_sp(
                builder=builder,
                shortest_path_analitics=shortest_path_analitics[str(builder)][hopcount],
                sim_duration=sim_duration,
                hopcount=hopcount,
            )
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("s, t")
        plt.ylabel("Average duration of best path from s to t")
        plt.title(
            f"Average duration of best path calculated with {builder.__name__} from s to t in {sim_duration} seconds of simulation."
        )
        # plt.savefig("images/adbp")
        plt.show()

    # -------------------------------------------
    # Average Duration same metric different builder

    for hopcount in [True, False]:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        for builder in builders:
            plot_average_duration_of_sp(
                builder=builder,
                shortest_path_analitics=shortest_path_analitics[str(builder)][hopcount],
                sim_duration=sim_duration,
                hopcount=hopcount,
            )
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("s, t")
        plt.ylabel("Average duration of best path from s to t")
        plt.title(
            f"Average duration of best path calculated with {'hopcount' if hopcount else 'distance'} from s to t in {sim_duration} seconds of simulation."
        )
        # plt.savefig("images/adbp")
        plt.show()

    # -------------------------------------------
    # Average length same metric different builder

    for builder in builders:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        for hopcount in [True, False]:
            plot_average_distance_of_sp(
                builder=builder,
                shortest_path_analitics=shortest_path_analitics[str(builder)][hopcount],
                hopcount=hopcount,
            )
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("s, t")
        plt.ylabel("Average distance of best path from s to t")
        plt.title(
            f"Average duration of best path calculated with {'hopcount' if hopcount else 'distance'} from s to t in {sim_duration} seconds of simulation."
        )
        # plt.savefig("images/adbp")
        plt.show()

    # -------------------------------------------
    # Average length same builder different metric

    for hopcount in [True, False]:
        plt.figure(figsize=(15, 8))
        ax = plt.subplot()
        for builder in builders:
            plot_average_distance_of_sp(
                builder=builder,
                shortest_path_analitics=shortest_path_analitics[str(builder)][hopcount],
                hopcount=hopcount,
            )
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xlabel("s, t")
        plt.ylabel("Average duration of best path from s to t")
        plt.title(
            f"Average duration of best path calculated with {builder.__name__} from s to t in {sim_duration} seconds of simulation."
        )
        # plt.savefig("images/adbp")
        plt.show()
