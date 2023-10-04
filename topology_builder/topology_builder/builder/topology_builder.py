import itertools
import math
from typing import Any, Dict, List, Self
from skyfield.api import load, wgs84, utc
from datetime import datetime
from topology_builder.repository.satellite_repository import LeoSatelliteRepository
from topology_builder.topology.topology import Topology
from topology_builder.node_types import NodeTypes


class TopologyBuilder:
    def __init__(
        self, verbose: bool, name: str, t: datetime = datetime.now(tz=utc)
    ) -> None:
        self.verbose = verbose
        self.t = load.timescale().from_datetime(t)
        self.topology = Topology(name, self.t)

    def _los_between_satellites(self, sat_u: str, sat_v: str) -> bool:
        # Get position vertors
        pos_u = self.topology.get_position(sat_u).position.km
        pos_v = self.topology.get_position(sat_v).position.km

        num = sum(pos_u[:] * pos_u[:]) * sum(pos_v[:] * pos_v[:]) - math.pow(
            sum(pos_u[:] * pos_v[:]), 2
        )
        den = (
            sum(pos_u[:] * pos_u[:])
            + sum(pos_v[:] * pos_v[:])
            - 2 * sum(pos_u[:] * pos_v[:])
        )

        res = math.sqrt(abs(num / den)) - 6378.14  # Earth radius

        return res > 0

    def _get_closer_satellite_to_gs(self, gs: str) -> Dict[str, Any]:
        """
        Return closer satellite to gs
        """
        satellites: List[str] = self.topology.get_leo_satellites()
        # Closer until now
        closer = dict()
        # Initialization
        closer["distance"] = math.inf  # heigth from GS
        closer["satellite"] = satellites[0]  # Candidate satellite
        # Iterate over the candidate satellites except the first
        for sat in satellites:
            # Get alt and distance
            alt, _, distance = self.topology.get_difference(sat, gs).altaz()
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

    def get_closer_sat_next_plane(self, satellite: str) -> Dict[str, Any]:
        current_plane = self.topology.get_sat_plane(satellite)

        satellites_next_plane_los = [
            sat
            for sat in self.topology.get_leo_satellites()
            if self.topology.get_sat_plane(sat)
            == (current_plane + 1) % self.topology.no_planes
            and self._los_between_satellites(satellite, sat)
        ]

        min_dist_next_plane = min(
            satellites_next_plane_los,
            key=lambda x: self.topology.get_difference(x, satellite).distance().km,
        )

        return {
            "satellite": min_dist_next_plane,
            "distance": self.topology.get_difference(min_dist_next_plane, satellite)
            .distance()
            .km,
        }

    def _add_intra_plane_links(self, satellite: str) -> List[Dict[str, Any]]:
        current_plane = self.topology.get_sat_plane(satellite)
        current_position_in_plane = self.topology.get_position_in_plane(satellite)

        candidates = []

        for sat in self.topology.get_leo_satellites():
            if sat == satellite:
                continue
            if self.topology.get_sat_plane(sat) != current_plane:
                continue
            if not self._los_between_satellites(satellite, sat):
                continue
            if not (
                self.topology.get_position_in_plane(sat)
                == (current_position_in_plane + 1) % self.topology.no_sat_per_plane
                or self.topology.get_position_in_plane(sat)
                == (current_position_in_plane - 1) % self.topology.no_sat_per_plane
            ):
                continue

            candidates.append(
                {
                    "satellite": sat,
                    "distance": self.topology.get_difference(sat, satellite)
                    .distance()
                    .km,
                }
            )

        return candidates

    def _add_inter_plane_links(self, satellite: Dict[Any, Any]) -> Dict[str, Any]:
        pass

    def _get_sat_for_building_gsl(self, gs: str) -> Dict[str, Any]:
        pass

    # Public Methods

    def add_LEO_constellation(self, repository: LeoSatelliteRepository) -> Self:
        """Adds LEO satllites to the Topology

        Args:
            repository (LeoSatelliteRepository): represents a data source for the satellite constellation

        Returns:
            self: part of the builder pattern
        """

        constellation = repository.get_constellation()

        if self.verbose:
            print(f"\nAdding {len(constellation)} LEO satellites")

        self.topology.ntwk.add_nodes_from(
            [
                (
                    name,
                    dict(
                        info,
                        **{
                            "latitude": wgs84.latlon_of(
                                info["skyfield_obj"].at(self.t)
                            )[0].degrees,
                            "longitude": wgs84.latlon_of(
                                info["skyfield_obj"].at(self.t)
                            )[1].degrees,
                            "height": wgs84.height_of(
                                info["skyfield_obj"].at(self.t)
                            ).km,
                        },
                    ),
                )
                for name, info in constellation
            ]
        )

        self.topology.no_planes = max([info["plane"] for _, info in constellation]) + 1

        self.topology.no_sat_per_plane = (
            max([info["position_in_plane"] for _, info in constellation]) + 1
        )

        if self.verbose:
            print(f"Number of planes : {self.topology.no_planes}")
            print(f"Number of per plane : {self.topology.no_sat_per_plane}")

        return self

    def add_GSs(self, groud_stations: List[Dict[Any, Any]]) -> Self:
        """
        Add Ground Stations to the Topology
        """

        if self.verbose:
            print(f"\nBuilding {len(groud_stations)} GSs.")

        # Build skyfield's GeographicPosition object as well as the name of the GS
        gs_s_topo = [
            (
                groud_station["name"],
                {
                    "skyfield_obj": wgs84.latlon(
                        groud_station["lat"], groud_station["lon"]
                    ),
                    "latitude": wgs84.latlon(
                        groud_station["lat"], groud_station["lon"]
                    ).latitude.degrees,
                    "longitude": wgs84.latlon(
                        groud_station["lat"], groud_station["lon"]
                    ).longitude.degrees,
                    "type": NodeTypes.GROUD_STATION,
                },
            )
            for groud_station in groud_stations
        ]

        # Add to the network
        self.topology.ntwk.add_nodes_from(gs_s_topo)

        return self

    def add_ISLs(self) -> Self:
        """
        Add ISLs based on the four closer satellites.
        """

        satellites = self.topology.get_leo_satellites()

        if len(satellites) == 0:
            raise Exception(
                "The number of satellites in the topology should not be 0 for building ISLs."
            )

        if self.verbose:
            print("\nAdding ISLs...")

        for i, satellite in enumerate(satellites):
            # Print logs every 10% of the progress
            if self.verbose and i % int(0.1 * len(satellites)) == 0:
                print(f"progressing... satellite {i + 1} of {len(satellites)}")

            candidates = itertools.chain(
                self._add_intra_plane_links(satellite),
                [self._add_inter_plane_links(satellite)],
            )

            [
                self.topology.ntwk.add_edge(
                    satellite, candidate["satellite"], length=candidate["distance"]
                )
                for candidate in candidates
            ]

        return self

    def add_GSLs(self) -> Self:
        """
        Build ground-to-satellite link based on the closer satellite to every GS.
        """

        if self.verbose:
            print("\nBuilding GSLs...")

        # At least one satellite needs to be present
        if len(self.topology.get_leo_satellites()) == 0:
            raise Exception(
                "The number of satellites in the topology should not be 0 when building GSLs."
            )

        # Get Ground Stations
        gs_s = self.topology.get_GSs()

        # At least one satellite needs to be present
        if len(gs_s) == 0:
            raise Exception(
                "The number of ground stations in the topology should not be 0 when building GSLs."
            )

        for i, gs in enumerate(gs_s):
            # Get closer satellite to gs
            closer_satellite = self._get_sat_for_building_gsl(gs=gs)

            if self.verbose:
                print(f"Adding GSL {i + 1}/{len(gs_s)}.")

            self.topology.ntwk.add_edge(
                gs,  # gs
                closer_satellite["satellite"],  # Satellite
                length=closer_satellite["distance"],  # Distance
            )

        return self

    def build(self) -> Topology:
        return self.topology
