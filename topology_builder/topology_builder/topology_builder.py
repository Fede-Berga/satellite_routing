import copy
import math
import os
import sys
from typing import Any, Dict, List, Self
from skyfield.api import load, wgs84, EarthSatellite, utc
from skyfield.toposlib import GeographicPosition
from datetime import datetime

sys.path.append(os.path.abspath("./topology_builder"))
from satellite_repository import LeoSatelliteRepository
from topology import Topology

class TopologyBuilder:
    def __init__(
        self, verbose: bool, name: str, t: datetime = datetime.now(tz=utc)
    ) -> None:
        self.verbose = verbose
        self.t = load.timescale().from_datetime(t)
        self.topology = Topology(name, self.t)

    # Private Methods

    def _los_between_satellites(
        self, sat_u: EarthSatellite, sat_v: EarthSatellite
    ) -> bool:
        # Get position vertors
        pos_u = sat_u.at(self.t).position.km
        pos_v = sat_v.at(self.t).position.km

        num = sum(pos_u[:] * pos_u[:]) * sum(pos_v[:] * pos_v[:]) - math.pow(
            sum(pos_u[:] * pos_v[:]), 2
        )
        den = (
            sum(pos_u[:] * pos_u[:])
            + sum(pos_v[:] * pos_v[:])
            - 2 * sum(pos_u[:] * pos_v[:])
        )

        res = math.sqrt(num / den) - 6378.14  # Earth radius

        return res > 0

    def _get_closer_satellite_to_gs(
        self,
        gs: GeographicPosition,  # Target GS
    ) -> Dict[Any, Any]:
        """
        Return closer satellite to gs
        """
        satellites = self.topology.get_satellites()
        # Closer until now
        closer = dict()
        # Initialization
        closer["distance"] = math.inf  # heigth from GS
        closer["satellite"] = satellites[0]  # Candidate satellite
        # Iterate over the candidate satellites except the first
        for sat in satellites:
            # Get alt and distance
            alt, _, distance = (sat - gs).at(self.t).altaz()
            # below the horizon
            if alt.degrees <= 0:
                continue
            # Build candidate
            candidate = {"satellite": sat, "distance": distance.km}
            # Update closer satellite
            closer = (
                closer
                if min(closer["distance"], candidate["distance"]) == closer["distance"]
                else candidate
            )

        return closer

    def _add_intra_plane_links(self, satellite: Dict[Any, Any]) -> None:
        current_plane = self.topology.ntwk.nodes[satellite]["plane"]
        current_position_in_plane = self.topology.ntwk.nodes[satellite][
            "position_in_plane"
        ]

        for x, y in self.topology.ntwk.nodes(data=True):
            if x == satellite:
                continue
            if type(x) != EarthSatellite:
                continue
            if y["plane"] != current_plane:
                continue
            if not self._los_between_satellites(satellite, x):
                continue
            if not (
                y["position_in_plane"]
                == (current_position_in_plane + 1) % self.topology.no_sat_per_plane
                or y["position_in_plane"]
                == (current_position_in_plane - 1) % self.topology.no_sat_per_plane
            ):
                continue

            self.topology.ntwk.add_edge(
                satellite, x, length=(x.at(self.t) - satellite.at(self.t)).distance().km
            )

    def _add_inter_plane_links(self, satellite: Dict[Any, Any]) -> None:
        pass

    def _get_sat_for_building_gsl(self, gs: GeographicPosition) -> Dict[Any, Any]:
        pass

    # Public Methods

    def add_LEO_constellation(self, repository: LeoSatelliteRepository) -> Self:
        """Adds LEO satllites to the Topology

        Args:
            repository (LeoSatelliteRepository): represents a data source for the satellite constellation

        Returns:
            self: part of the builder pattern
        """

        if self.verbose:
            print(f"\nAdding {len(repository.get_constellation())} leo satellites")

        self.topology.ntwk.add_nodes_from(
            [
                (
                    satellite["satellite"],
                    {
                        "plane": satellite["plane"],
                        "position_in_plane": satellite["position_in_plane"],
                    },
                )
                for satellite in repository.get_constellation()
            ]
        )

        self.topology.no_planes = (
            max([satellite["plane"] for satellite in repository.get_constellation()])
            + 1
        )
        self.topology.no_sat_per_plane = (
            max(
                [
                    satellite["position_in_plane"]
                    for satellite in repository.get_constellation()
                ]
            )
            + 1
        )

        if self.verbose:
            print(f"no planes : {self.topology.no_planes}")
            print(f"no satellites per plane : {self.topology.no_sat_per_plane}")

        return self

    def add_GSs(self, groud_stations: List[Dict[Any, Any]]) -> Self:
        """
        Add Ground Stations to the Topology
        """

        if self.verbose:
            print("\nBuilding GSs...")

        # Build skyfield's GeographicPosition object as well as the name of the GS
        gs_s_topo = [
            (
                wgs84.latlon(groud_station["lat"], groud_station["lon"]),  # GS
                {"name": groud_station["name"]},  # Attributes : name
            )
            for groud_station in groud_stations
        ]

        if self.verbose:
            print(f"Add : {len(gs_s_topo)} Ground Stations")

        # Add to the network
        self.topology.ntwk.add_nodes_from(gs_s_topo)

        return self

    def add_ISLs(self) -> Self:
        """
        Add ISLs based on the four closer satellites.
        """

        satellites = self.topology.get_satellites()

        if len(satellites) == 0:
            raise Exception(
                "The number of satellites in the topology should not be 0 for building ISLs."
            )

        if self.verbose:
            print("\nAdding ISLs...")

        for i, satellite in enumerate(satellites):
            # Print logs every 10% of the progress
            if self.verbose and i % int(0.1 * len(list(self.topology.ntwk.nodes))) == 0:
                print(
                    f"progressing... satellite {i + 1} of {len(list(self.topology.ntwk.nodes))}"
                )

            self._add_intra_plane_links(satellite)
            self._add_inter_plane_links(satellite)

        #print(f"Graph: {self.topology.ntwk}")

        #for satellite in satellites: 
            #if len(list(self.topology.ntwk.neighbors(satellite))) != 4:
                #print(
                #    f"\nadj[{satellite.name}] has length {len(list(self.topology.ntwk.neighbors(satellite)))}"
                #)
                #print(
                #    f"adj[{satellite.name}] : {list(self.topology.ntwk.neighbors(satellite))}"
                #)
                #raise Exception()

        return self

    def add_GSLs(self) -> Self:
        """
        Build ground-to-satellite link based on the closer satellite to every GS.
        """

        if self.verbose:
            print("\nBuilding GSLs...")

        # At least one satellite needs to be present
        if len(self.topology.get_satellites()) == 0:
            raise Exception(
                "The number of satellites in the topology should not be 0 when building GSLs."
            )

        # Get Ground Stations
        gs_s = self.topology.get_GSs()

        for i, gs in enumerate(gs_s):
            # Get closer satellite to gs
            closer_satellite = self._get_sat_for_building_gsl(gs=gs)

            if self.verbose:
                print(f"Adding GSL {i + 1}/{len(gs_s)} ...")

            self.topology.ntwk.add_edge(
                gs,  # gs
                closer_satellite["satellite"],  # Satellite
                length=closer_satellite["distance"],  # Distance
            )

        return self

    def build(self) -> Topology:
        return self.topology


class MinimumDistanceTopologyBuilder(TopologyBuilder):
    def __init__(
        self, verbose: bool, name: str, t: datetime = datetime.now(tz=utc)
    ) -> None:
        super().__init__(verbose, name, t)

    def _add_inter_plane_links(self, satellite: Dict[Any, Any]) -> None:
        # print("inter plane MINDIST...")
        current_plane = self.topology.ntwk.nodes[satellite]["plane"]

        satellites_next_plane_los = [
            x
            for x, y in self.topology.ntwk.nodes(data=True)
            if type(x) == EarthSatellite
            and y["plane"] == (current_plane + 1) % self.topology.no_planes
            and self._los_between_satellites(satellite, x)
        ]

        # print(
        #     f"satellites_next_plane_los: {[(sat.name, (sat.at(self.t) - satellite.at(self.t)).distance().km) for sat in satellites_next_plane_los]}"
        # )

        """
        satellites_previous_plane_los = [
            x
            for x, y in self.topology.ntwk.nodes(data=True)
            if type(x) == EarthSatellite
            and y["plane"] == (current_plane - 1) % self.topology.no_planes
            and self._los_between_satellites(satellite, x)
        ]

        print(f"\nsatellites_previous_plane_los: {[(sat.name, (sat.at(self.t) - satellite.at(self.t)).distance().km, (satellite.at(self.t) - sat.at(self.t)).distance().km) for sat in satellites_previous_plane_los]}")
       
        min_dist_prev_plane = min(
            satellites_previous_plane_los,
            key=lambda x: (x.at(self.t) - satellite.at(self.t)).distance().km,
        )
        print(f"min_dist_prev_plane: {min_dist_prev_plane}")
        """

        min_dist_next_plane = min(
            satellites_next_plane_los,
            key=lambda x: (x.at(self.t) - satellite.at(self.t)).distance().km,
        )

        #print(f"min_dist_next_plane: {min_dist_next_plane}")

        self.topology.ntwk.add_edge(
            satellite,
            min_dist_next_plane,
            length=(min_dist_next_plane.at(self.t) - satellite.at(self.t))
            .distance()
            .km,
        )

    def _get_sat_for_building_gsl(self, gs: GeographicPosition) -> Dict[Any, Any]:
        return self._get_closer_satellite_to_gs(gs)


class LOSTopologyBuilder(TopologyBuilder):
    def __init__(
        self,
        verbose: bool,
        name: str,
        previous_topology: Topology,
        t: datetime = datetime.now(tz=utc),
    ) -> None:
        super().__init__(verbose, name, t)
        self.previous_topology = previous_topology

    def _add_inter_plane_links(self, satellite: Dict[Any, Any]) -> None:
        current_plane = self.topology.ntwk.nodes[satellite]["plane"]

        prev_satellite = [
            sat
            for sat in self.previous_topology.get_satellites()
            if sat.name == satellite.name
        ][0]

        # print(f"\n{satellite.name}")

        for neigh_prev in self.previous_topology.ntwk.neighbors(prev_satellite):
            if (
                type(neigh_prev) != EarthSatellite
                or self.previous_topology.ntwk.nodes[neigh_prev]["plane"]
                == current_plane
            ):
                continue

            neigh_current = [
                sat
                for sat in self.topology.get_satellites()
                if sat.name == neigh_prev.name
            ][0]

            if self._los_between_satellites(satellite, neigh_current):
                # print(f"{satellite.name} and {neigh.name} are los at distance {(neigh.at(self.t) - prev_satellite.at(self.t)).distance().km}")
                self.topology.ntwk.add_edge(
                    satellite,
                    neigh_current,
                    length=(neigh_current.at(self.t) - satellite.at(self.t))
                    .distance()
                    .km,
                )
            else:
                neigh_plane = self.previous_topology.ntwk.nodes[neigh_prev]["plane"]

                satellites_neigh_plane_los_current_topo = [
                    x
                    for x, y in self.topology.ntwk.nodes(data=True)
                    if type(x) == EarthSatellite
                    and y["plane"] == neigh_plane
                    and self._los_between_satellites(satellite, x)
                ]

                min_dist_neigh_plane = min(
                    satellites_neigh_plane_los_current_topo,
                    key=lambda x: (x.at(self.t) - satellite.at(self.t)).distance().km,
                )

                #print(f"min_dist_neigh_plane : {min_dist_neigh_plane}")

                self.topology.ntwk.add_edge(
                    satellite,
                    min_dist_neigh_plane,
                    length=(min_dist_neigh_plane.at(self.t) - satellite.at(self.t))
                    .distance()
                    .km,
                )

    def _get_sat_for_building_gsl(self, gs: GeographicPosition) -> Dict[Any, Any]:
        for node in self.previous_topology.get_GSs():
            if not (
                node.latitude.degrees == gs.latitude.degrees
                and node.longitude.degrees == gs.longitude.degrees
            ):
                continue

            prev_sat = next(self.previous_topology.ntwk.neighbors(node))

            sat = [
                x for x in self.topology.get_satellites() if x.name == prev_sat.name
            ][0]

            # Get alt and distance
            alt, _, distance = (prev_sat - gs).at(self.t).altaz()
            # below the horizon
            if alt.degrees <= 0:
                return self._get_closer_satellite_to_gs(gs)
            else:
                return {"satellite": sat, "distance": distance.km}
