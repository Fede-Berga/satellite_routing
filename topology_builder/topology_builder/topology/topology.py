import random
from typing import List, Self, Tuple
import networkx as nx, json
from skyfield.api import wgs84, Time
import matplotlib.pyplot as plt

#from mpl_toolkits.basemap import Basemap
import numpy as np
from itertools import chain, cycle
import matplotlib.colors as mcolors
from topology_builder.node_types import NodeTypes
from skyfield.positionlib import ICRF


class Topology:
    def __init__(self, name: str, t: Time) -> None:
        self.ntwk = nx.Graph()
        self.name: str = name
        self.t: Time = t
        self.no_planes: int = 0
        self.no_sat_per_plane: int = 0

    def __str__(self) -> str:
        nx_data = nx.node_link_data(self.ntwk)

        for node in nx_data["nodes"]:
            del node["skyfield_obj"]

        dict_graph = {
            "name": self.name,
            "t": self.t.utc_strftime(),
            "description": self.ntwk.__str__(),
            "no_planes": self.no_planes,
            "no_sat_per_plane": self.no_sat_per_plane,
            "networkx_obj": nx_data,
        }

        return json.dumps(
            dict_graph,
            indent=4,
            default=lambda o: "<not serializable>",
        )

    def __repr__(self) -> str:
        return self.__str__()

    def get_GSs(self) -> List[str]:
        return [
            node
            for node in self.ntwk.nodes
            if self.ntwk.nodes[node]["type"] == NodeTypes.GROUD_STATION
        ]

    def get_leo_satellites(self) -> List[str]:
        return [
            node
            for node in self.ntwk.nodes
            if self.ntwk.nodes[node]["type"] == NodeTypes.LEO_SATELLITE
        ]

    def get_ISLs(self) -> List[str]:
        return [
            (s, t)
            for s, t in self.ntwk.edges
            if self.ntwk.nodes[s]["type"] == NodeTypes.LEO_SATELLITE
            and self.ntwk.nodes[t]["type"] == NodeTypes.LEO_SATELLITE
        ]

    def get_GSLs(self) -> List[str]:
        return [
            (s, t)
            for s, t in self.ntwk.edges
            if self.ntwk.nodes[s]["type"] == NodeTypes.GROUD_STATION
            or self.ntwk.nodes[t]["type"] == NodeTypes.GROUD_STATION
        ]

    def get_sat_plane(self, satellite: str) -> int:
        return self.ntwk.nodes[satellite]["plane"]

    def get_position_in_plane(self, satellite: str) -> int:
        return self.ntwk.nodes[satellite]["position_in_plane"]

    def get_difference(self, u: str, v: str) -> ICRF:
        return self.ntwk.nodes[u]["skyfield_obj"].at(self.t) - self.ntwk.nodes[v][
            "skyfield_obj"
        ].at(self.t)

    def get_position(self, node: str) -> ICRF:
        return self.ntwk.nodes[node]["skyfield_obj"].at(self.t)

    def get_node_lat_lon(self, node: str):
        lat, long = wgs84.latlon_of(self.ntwk.nodes[node]["skyfield_obj"].at(self.t))
        return lat.degrees, long.degrees

    def is_different(self, other: Self):
        return nx.is_empty(nx.difference(other.ntwk, self.ntwk)) or nx.is_empty(
            nx.difference(self.ntwk, other.ntwk)
        )
    
    def get_diff_graph(self, other: Self) -> nx.Graph:
        return nx.difference(other.ntwk, self.ntwk)

"""

    def _plot_edges(self, edges: List[Tuple[str, str]], color=None):
        for u, v in edges:
            lat_u, lon_u = self.get_node_lat_lon(u)
            plt.plot(lon_u, lat_u, "ok", markersize=3)
            plt.text(lon_u, lat_u, u, fontsize=7)

            lat_v, lon_v = self.get_node_lat_lon(v)
            plt.plot(lon_v, lat_v, "ok", markersize=3)
            plt.text(lon_v, lat_v, v, fontsize=7)

            # u --- v
            plt.plot([lon_u, lon_v], [lat_u, lat_v], color=color)

    def _draw_map(self, m: Basemap, scale=0.2):
        # draw a shaded-relief image
        m.shadedrelief(scale=scale)

        # lats and longs are returned as a dictionary
        lats = m.drawparallels(np.linspace(-90, 90, 13))
        lons = m.drawmeridians(np.linspace(-180, 180, 13))

        # keys contain the plt.Line2D instances
        lat_lines = chain(*(tup[1][0] for tup in lats.items()))
        lon_lines = chain(*(tup[1][0] for tup in lons.items()))
        all_lines = chain(lat_lines, lon_lines)

        # cycle through these lines and set the desired style
        for line in all_lines:
            line.set(linestyle="-", alpha=0.3, color="w")

    def get_shuffled_matplotlib_colors(self) -> cycle:
        colors = list(mcolors.CSS4_COLORS.items())
        random.shuffle(colors)
        colors = dict(colors)
        return cycle(colors)

    def draw(self) -> None:
        plt.figure(figsize=(8, 6))

        m = Basemap(
            projection="cyl",
            resolution=None,
            llcrnrlat=-90,
            urcrnrlat=90,
            llcrnrlon=-180,
            urcrnrlon=180,
        )

        self._draw_map(m)

        colors = self.get_shuffled_matplotlib_colors()

        self._plot_edges(self.get_GSLs(), color=next(colors))
        self._plot_edges(self.get_ISLs(), color=next(colors))

        plt.show()

    def draw_paths(self, paths: List[List[str]]) -> None:
        m = Basemap(
            projection="cyl",
            resolution=None,
            llcrnrlat=-90,
            urcrnrlat=90,
            llcrnrlon=-180,
            urcrnrlon=180,
        )

        self._draw_map(m)

        colors = self.get_shuffled_matplotlib_colors()

        for path in paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            self._plot_edges(edges, color=next(colors))
    """
