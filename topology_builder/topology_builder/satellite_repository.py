from pathlib import Path
from typing import Any, Dict, List
from skyfield.api import load, EarthSatellite

class SatelliteRepository:
    def __init__(self) -> None:
        pass

    def get_constellation() -> Dict[str, Any]:
        pass


class LeoSatelliteRepository(SatelliteRepository):
    def __init__(self) -> None:
        super().__init__()

    def get_constellation() -> Dict[str, Any]:
        pass


class STKLeoSatelliteRepository(LeoSatelliteRepository):
    def __init__(self, file: Path) -> None:
        super().__init__()
        self.file: Path = file

    def _get_satellite_name_plane_pos_in_plane(
        self, names: str
    ) -> List[Dict[str, Any]]:
        """
        Return dict such as:
        {
            'name' : ..
            'plane' : ...
            'position_in_plane' : ...
        }
        """

        # names = names.strip().split()
        # match = re.search("^([A-Za-z0-9\-]+)\_([0-9]+)$", 'Iridium_116')
        # print(match.groups())

        return [
            {
                "name": f"Iridium{int(i / 6) + 1}{i % 6 + 1}",
                "plane": int(i / 6),
                "position_in_plane": i % 6,
            }
            for i in range(66)
        ]

    def get_constellation(self) -> Dict[str, Any]:
        with open(self.file, "r") as file:
            file.readline()  # First line is useless

            # Get names and positions
            sat_from_file = self._get_satellite_name_plane_pos_in_plane(file.readline())

            [file.readline() for _ in range(2)]  # Third and fourth lines are useless

            satellites = []
            for sat_info in sat_from_file:
                [file.readline() for _ in range(2)]  # First two lines are useless

                line_1 = file.readline().strip()
                line_2 = file.readline().strip()

                satellites.append(
                    {
                        "satellite": EarthSatellite(
                            line_1, line_2, sat_info["name"], load.timescale()
                        ),
                        "plane": sat_info["plane"],
                        "position_in_plane": sat_info["position_in_plane"],
                    }
                )

                [file.readline() for _ in range(2)]  # Last two lines are useless

        return satellites