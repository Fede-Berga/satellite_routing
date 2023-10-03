import random
from typing import Any, Dict, List
from click import Path
import networkx as nx, json
from skyfield.api import wgs84, EarthSatellite, Time
from skyfield.toposlib import GeographicPosition
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
from itertools import chain, cycle
import matplotlib.colors as mcolors


class Topology:
    def __init__(self, name: str, t: Time) -> None:
        self.ntwk = nx.Graph()
        self.name: str = name
        self.t: Time = t
        self.no_planes: int = 0
        self.no_sat_per_plane: int = 0

    def __str__(self) -> str:
        return json.dumps(
            self.to_json(), 
            indent=4, 
            #default=lambda o: o.name if isinstance(o, EarthSatellite) else self.ntwk.nodes[o]["name"],
        )

    def __repr__(self) -> str:
        return json.dumps(
            nx.node_link_data(self.ntwk), 
            indent=4, 
            default=lambda o: o.name if isinstance(o, EarthSatellite) else self.ntwk.nodes[o]["name"],
        )

    def get_GSs(self) -> List[GeographicPosition]:
        return [
            node for node in self.ntwk.nodes if isinstance(node, GeographicPosition)
        ]

    def get_satellites(self) -> List[GeographicPosition]:
        return [node for node in self.ntwk.nodes if isinstance(node, EarthSatellite)]

    def get_ISLs(self) -> None:
        return [
            edge
            for edge in self.ntwk.edges
            if isinstance(edge[0], EarthSatellite)
            and isinstance(edge[1], EarthSatellite)
        ]

    def get_GSLs(self) -> None:
        return [
            edge
            for edge in self.ntwk.edges
            if isinstance(edge[0], GeographicPosition)
            or isinstance(edge[1], GeographicPosition)
        ]

    def to_json(self) -> Dict[Any, Any]:
        return {
            "name": self.name,
            "graph": {
                "description": self.ntwk.__str__(),
                "satellites": [
                    {
                        "name": satellite.name,
                        "latitude": wgs84.latlon_of(satellite.at(self.t))[0].degrees,
                        "longitude": wgs84.latlon_of(satellite.at(self.t))[1].degrees,
                        "height": wgs84.height_of(satellite.at(self.t)).km,
                    }
                    for satellite in self.get_satellites()
                ],
                "ground_stations": [
                    {
                        "name": self.ntwk.nodes[node]["name"],
                        "latitude": node.latitude.degrees,
                        "longitude": node.longitude.degrees,
                    }
                    for node in self.get_GSs()
                ],
                "ISLs": [
                    {
                        "u": edge[0].name,
                        "v": edge[1].name,
                        "distance": self.ntwk[edge[0]][edge[1]]["length"],
                    }
                    for edge in self.get_ISLs()
                ],
                "GSLs": [
                    {
                        "u": edge[0].name
                        if isinstance(edge[0], EarthSatellite)
                        else self.ntwk.nodes[edge[0]]["name"],
                        "v": edge[1].name
                        if isinstance(edge[1], EarthSatellite)
                        else self.ntwk.nodes[edge[1]]["name"],
                        "distance": self.ntwk[edge[0]][edge[1]]["length"],
                    }
                    for edge in self.get_GSLs()
                ],
            },
        }

    def get_node_lat_lon_degrees(self, node: EarthSatellite | GeographicPosition):
        if type(node) == EarthSatellite:
            lat, long = wgs84.latlon_of(node.at(self.t))
            return lat.degrees, long.degrees
        
        return node.latitude.degrees, node.longitude.degrees

    def get_node_name(self, node: EarthSatellite | GeographicPosition):
        if type(node) == EarthSatellite:
            return node.name
        
        return self.ntwk.nodes[node]["name"]
    
    def _plot_edges(self, edges: List[GeographicPosition | EarthSatellite], color = None):
        for u, v in edges:
            lat_u, lon_u = self.get_node_lat_lon_degrees(u)
            u_name = self.get_node_name(u)
            plt.plot(lon_u, lat_u, "ok", markersize=3)
            plt.text(lon_u, lat_u, u_name, fontsize=7)

            lat_v, lon_v = self.get_node_lat_lon_degrees(v)
            v_name = self.get_node_name(v)
            plt.plot(lon_v, lat_v, "ok", markersize=3)
            plt.text(lon_v, lat_v, v_name, fontsize=7)

            # u --- v
            plt.plot([lon_u, lon_v], [lat_u, lat_v], color = color)

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
        self._plot_edges(self.get_GSLs())
        self._plot_edges(self.get_ISLs())

        plt.show()
    
    def draw_paths(self, paths : List[List[EarthSatellite|GeographicPosition]]) -> None :
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

        colors = list(mcolors.CSS4_COLORS.items())
        random.shuffle(colors)
        colors = dict(colors)
        colors = cycle(colors)

        for path in paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            self._plot_edges(edges, color=next(colors))

        plt.show()