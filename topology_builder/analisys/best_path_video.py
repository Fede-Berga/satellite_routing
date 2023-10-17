import random
import matplotlib.colors as mcolors
import datetime
from itertools import combinations, cycle
from pathlib import Path
import numpy as np
import yaml
import networkx as nx
import matplotlib.pyplot as plt
import sys
import os
import cv2
import os

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

    gs_s = config["ground_stations"][:3]

    constellation_path = config["constellation_file"]

    name = config["name"]

    return name, start_time, end_time, dt, constellation_path, gs_s


def collect_sp_analitics(
    builder_cls: type[LOSTopologyBuilder | MinimumDistanceTopologyBuilder],
    save_paths_img_path: Path = None
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
        paths = []

        for s, t in s_t_couples:
            p = nx.shortest_path(
                G=current_topology.ntwk,
                source=s,
                target=t,
                weight="length",
            )
            paths.append(p)
        
        # plot
        plt.figure(figsize=(8, 6))

        current_topology.draw_paths(paths)

        if save_paths_img_path != None:
            plt.savefig(os.path.join(save_paths_img_path, f"bp_{(now - start_time).seconds}"))
            plt.close()
        else:
            plt.show()

        now = now + datetime.timedelta(milliseconds=dt)

if __name__ == "__main__":
    builders = [LOSTopologyBuilder, MinimumDistanceTopologyBuilder]

    # Collect Analitics
    for builder in builders:
        image_folder = Path(f'tmp/{builder.__name__}_paths_images/')
        video_name = f'{builder.__name__}_video.avi'
        if not image_folder.exists():
            image_folder.mkdir(parents=True, exist_ok=True)

        collect_sp_analitics(builder, image_folder)

        images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape

        video = cv2.VideoWriter(video_name, 0, 1, (width,height))

        for image in images:
            video.write(cv2.imread(os.path.join(image_folder, image)))

        cv2.destroyAllWindows()
        video.release()
