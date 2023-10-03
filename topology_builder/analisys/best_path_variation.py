from collections import defaultdict
import datetime
from itertools import combinations
import json
import os
from pathlib import Path
import sys
import time
from numpy import mean
import yaml
from skyfield.api import EarthSatellite
import networkx as nx
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath("./"))
from topology_builder.satellite_repository import STKLeoSatelliteRepository
from topology_builder.topology_builder import (
    MinimumDistanceTopologyBuilder,
    LOSTopologyBuilder,
)


def main(verbose: bool = True):
    no_topo_builder = 2
    shortest_path_stats = []

    for i in range(no_topo_builder):
        # Open config File
        with open("./config.yaml", "r") as yamlfile:
            config = yaml.load(yamlfile, Loader=yaml.FullLoader)
            print("\nRead config successful")
            print(json.dumps(config, indent=4))

        # Fetch Paramenters
        dt = config["dt"]

        now = start_sym = datetime.datetime.strptime(
            config["start_time"], "%Y-%m-%d %H:%M:%S %z"
        )

        end_time = datetime.datetime.strptime(
            config["end_time"], "%Y-%m-%d %H:%M:%S %z"
        )

        current_topology = (
            MinimumDistanceTopologyBuilder(verbose=False, name=config["name"], t=now)
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path(config["constellation_file"]))
            )
            .add_ISLs()
            .add_GSs(config["ground_stations"])
            .add_GSLs()
            .build()
        )

        # with open(f"iridium_{now}.json", "w") as f:
        #     json.dump(current_topology.to_json(), f, indent=4)

        # break

        now += datetime.timedelta(milliseconds=dt)

        start_time = time.time()

        shortest_path_stats.append(dict())

        while now <= end_time:
            if verbose:
                print(f"Building topology at {now}")

            previous_topology = current_topology

            if i == 0:
                current_topology = (
                    LOSTopologyBuilder(
                        verbose=False,
                        name=config["name"],
                        t=now,
                        previous_topology=previous_topology,
                    )
                    .add_LEO_constellation(
                        STKLeoSatelliteRepository(Path(config["constellation_file"]))
                    )
                    .add_ISLs()
                    .add_GSs(config["ground_stations"])
                    .add_GSLs()
                    .build()
                )
            else:
                current_topology = (
                    LOSTopologyBuilder(
                        verbose=False,
                        name=config["name"],
                        t=now,
                        previous_topology=previous_topology,
                    )
                    .add_LEO_constellation(
                        STKLeoSatelliteRepository(Path(config["constellation_file"]))
                    )
                    .add_ISLs()
                    .add_GSs(config["ground_stations"])
                    .add_GSLs()
                    .build()
                )

            # Collecting shortest path statistics
            s_t_couples = list(combinations(current_topology.get_GSs(), 2))

            for s, t in s_t_couples:
                p = nx.shortest_path(G=current_topology.ntwk, source=s, target=t)

                s_name = current_topology.ntwk.nodes[s]["name"]
                t_name = current_topology.ntwk.nodes[t]["name"]

                if s_name not in shortest_path_stats[i].keys():
                    shortest_path_stats[i][s_name] = {}

                if t_name not in shortest_path_stats[i][s_name].keys():
                    shortest_path_stats[i][s_name][t_name] = []

                k = next(
                    (
                        j
                        for j, d in enumerate(shortest_path_stats[i][s_name][t_name])
                        if str(p) == d["path"]
                    ),
                    None,
                )

                if k == None:
                    shortest_path_stats[i][s_name][t_name].append(
                        {
                            "path": str(p),
                            "hops": len(p),
                            "frequence": 0,
                        }
                    )
                else:
                    shortest_path_stats[i][s_name][t_name][k]["frequence"] += 1

            # print(json.dumps(shortest_path_stats, indent=4))

            paths = [nx.shortest_path(G=current_topology.ntwk, source=s, target=t, 
                                      #weight='length'
                                      ) for s, t in s_t_couples]
            current_topology.draw_paths(paths)

            now += datetime.timedelta(milliseconds=dt)

        if verbose:
            print(f"\nThe simulation took {(time.time() - start_time) / 60} minutes")

    gs_names = [
        current_topology.ntwk.nodes[gs]["name"] for gs in current_topology.get_GSs()
    ]

    gs_names_couple_index = [
        (s, t)
        for t in gs_names
        for s in gs_names
        if s in shortest_path_stats[0].keys() and t in shortest_path_stats[0][s].keys()
    ]

    # print(gs_names_couple_index)

    # Average duration of best path from s to t

    plt.figure(figsize=(15, 6))

    for i in range(no_topo_builder):
        print(
            [
                (end_time - start_sym).seconds / len(shortest_path_stats[i][s][t])
                for (s, t) in gs_names_couple_index
            ]
        )
        plt.plot(
            [f"{str(s)}, {str(t)}" for s, t in gs_names_couple_index],
            [
                (end_time - start_sym).seconds / len(shortest_path_stats[i][s][t])
                for (s, t) in gs_names_couple_index
            ],
            "-o",
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
            # alpha = 0.7
        )
        plt.axhline(
            sum(
                (end_time - start_sym).seconds / len(shortest_path_stats[i][s][t])
                for (s, t) in gs_names_couple_index
            )
            / len(gs_names_couple_index),
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )

    # Plot Labels
    plt.legend()
    plt.xlabel("s, t")
    plt.ylabel("Average duration of best path from s to t")
    plt.title(
        f"Average duration of best path from s to t in {end_time - start_sym} of simulation."
    )
    plt.savefig("images/adbp")
    plt.show()

    # Average hop count of best path from s to t

    plt.figure(figsize=(15, 6))

    for i in range(no_topo_builder):
        plt.plot(
            [f"{str(s)}, {str(t)}" for s, t in gs_names_couple_index],
            [
                sum(
                    [
                        path["hops"] * path["frequence"]
                        for path in shortest_path_stats[i][s][t]
                    ]
                )
                / (end_time - start_sym).seconds
                for (s, t) in gs_names_couple_index
            ],
            "-o",
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
            alpha=0.7,
        )
        plt.axhline(
            sum(
                sum(
                    [
                        path["hops"] * path["frequence"]
                        for path in shortest_path_stats[i][s][t]
                    ]
                )
                / (end_time - start_sym).seconds
                for (s, t) in gs_names_couple_index
            )
            / len(gs_names_couple_index),
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )

    # Plot Labels
    plt.legend()
    plt.xlabel("s, t")
    plt.ylabel("Average length of best path from s to t weighted by its duration")
    plt.title(
        f"Average length of best path from s to t weighted by its duration in {end_time - start_sym} of simulation."
    )
    plt.savefig("images/albp")
    plt.show()


if __name__ == "__main__":
    main()
