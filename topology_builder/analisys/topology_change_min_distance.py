from collections import defaultdict
import datetime
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
    change_time_istant = [[]] * no_topo_builder
    mean_length_link = [[]] * no_topo_builder
    stability_intervals = [[]] * no_topo_builder
    no_link_changes = [defaultdict(int)] * no_topo_builder
    no_per_sat_link_variations = [defaultdict(int)] * no_topo_builder

    for i in range(no_topo_builder):
        # Opem config File
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

        now += datetime.timedelta(milliseconds=dt)

        change_time_istant[i] = [now]
        mean_length_link[i] = []
        no_link_changes[i] = defaultdict(int)
        no_per_sat_link_variations[i] = defaultdict(int)

        start_time = time.time()

        while now <= end_time:
            if verbose:
                print(f"Building topology at {now}")

            previous_topology = current_topology

            if i == 0:
                current_topology = (
                    MinimumDistanceTopologyBuilder(
                        verbose=False,
                        name=config["name"],
                        t=now,
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

            # Collecting Topology change stats

            edges_prev = [(u.name, v.name) for u, v in previous_topology.get_ISLs()] + [
                (
                    u.name,
                    previous_topology.ntwk.nodes[v]["name"],
                )
                if type(u) == EarthSatellite
                else (
                    previous_topology.ntwk.nodes[u]["name"],
                    v.name,
                )
                for u, v in previous_topology.get_GSLs()
            ]

            edges_current = [
                (u.name, v.name) for u, v in current_topology.get_ISLs()
            ] + [
                (u.name, current_topology.ntwk.nodes[v]["name"])
                if type(u) == EarthSatellite
                else (current_topology.ntwk.nodes[u]["name"], v.name)
                for u, v in current_topology.get_GSLs()
            ]

            sym_diff = set(edges_prev).symmetric_difference(set(edges_current))

            if len(sym_diff) > 0:
                change_time_istant[i].append(now)
                no_link_changes[i][len(sym_diff)] += 1

                for u, v in set(edges_current) - set(edges_prev):
                    no_per_sat_link_variations[i][u] += 1
                    no_per_sat_link_variations[i][v] += 1

                print(set(edges_current) - set(edges_prev))
                print(json.dumps(no_per_sat_link_variations, indent=4))

            # Collecting Link Length stats
            mean_length_link[i].append(
                sum(
                    [
                        nx.get_edge_attributes(current_topology.ntwk, "length")[edge]
                        for edge in current_topology.ntwk.edges
                    ]
                )
                / len(list(current_topology.ntwk.edges))
            )

            now += datetime.timedelta(milliseconds=dt)

        if verbose:
            print(f"\nThe simulation took {(time.time() - start_time) / 60} minutes")

        # Collecting Stability Intervals
        stability_intervals[i] = [
            (change_time_istant[i][j + 1] - change_time_istant[i][j]).seconds
            for j in range(len(change_time_istant[i]) - 1)
        ]

    # Plot stability interval stats

    for i in range(2):
        plt.hist(
            stability_intervals[i],
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )
        plt.axvline(
            sum(stability_intervals[i])
            / (len(change_time_istant[i]) - 1),  # Average interval change
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )

    # Plot Labels
    plt.legend()
    plt.xlabel("Frequency")
    plt.ylabel("Duration of stability intervals")
    plt.title(f"Frequency of stability intervals in {end_time - start_sym}")
    plt.savefig("images/stability_intervals_frequences")
    plt.show()

    # Length analisys
    for i in range(2):
        plt.hist(
            mean_length_link[i],
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )
        plt.axvline(
            mean(mean_length_link[i]),
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )

    # Plot Labels
    plt.legend()
    plt.xlabel("Frequency")
    plt.ylabel("Average length of link in a single topology")
    plt.title(
        f"Frequency of mean link length in the calculated topology in {end_time - start_sym}"
    )
    plt.savefig("images/average_length_links")
    plt.show()

    # Number of link changes
    for i in range(2):
        sorted_no_link_change = list(no_link_changes[i].keys())
        sorted_no_link_change.sort()
        #print(sorted_no_link_change)
        sorted_no_link_change = {j: no_link_changes[i][j] for j in sorted_no_link_change}
        plt.plot(
            list(sorted_no_link_change.keys()),
            list(sorted_no_link_change.values()),
            "-o",
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )
        plt.axhline(
            sum(value for _, value in sorted_no_link_change.items())
            / len(sorted_no_link_change),
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )

    # Plot Labels
    plt.legend()
    plt.xlabel("Number of link changes of the entire topology through the timesteps.")
    plt.ylabel("Number of times in which that number of changes occur.")
    plt.title(
        f"Number of link changes of the entire topology in {end_time - start_sym} of simulation."
    )
    plt.savefig("images/nlcet")
    plt.show()

    # Number of link changes per satellite
    for i in range(2):
        num_satellites_per_num_changes = defaultdict(int)
        for _, value in no_per_sat_link_variations[i].items():
            num_satellites_per_num_changes[value] += 1
        sorted = list(num_satellites_per_num_changes.keys())
        sorted.sort()
        sorted = {
            j: num_satellites_per_num_changes[j] for j in sorted
        }
        plt.plot(
            list(sorted.keys()),
            list(sorted.values()),
            "-o",
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )
        plt.legend()
        """
        plt.axhline(
            sum(value for _, value in sorted_no_link_change.items()) / len(sorted_no_link_change),
            color="k" if i == 0 else "c",
            linestyle="dashed",
            linewidth=1,
            label="MinimumDistanceTopologyBuilder" if i == 0 else "LOSTopologyBuilder",
        )
        """

    # Plot Labels
    plt.legend()
    plt.xlabel("Number of changes through the timesteps")
    plt.ylabel("Number of satellites that experiece those number of changes")
    plt.title(
        f"Number of satellites that experiece a certain number of chages in {end_time - start_sym} of simulation time."
    )
    plt.savefig("images/ncss")
    plt.show()

if __name__ == "__main__":
    main()
