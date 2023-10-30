from ast import Tuple
from itertools import combinations
from typing import Any, Dict, List
import sys
import geopy.distance
import numpy as np


def build_traffic_matrix(cities : List[Dict[str, Any]], total_volume_of_traffic: float) -> Dict[str, Dict[str, float]]:
    #pairwise_distance: Dict[str, Dict[str, float]] = dict()
    p_in: Dict[str, float] = dict()
    p_out: Dict[str, float] = dict()
    total_population = sum([city['population'] for city in cities])
    traffic_matrix_dict = dict()

    print(total_population, file=sys.stderr)

    """
    for s in cities:
        for t in cities:
            coords_s = (s['latitude'], s['longitude'])
            coords_t = (t['latitude'], t['longitude'])
            pairwise_distance[s['name'], t['name']] = geopy.distance.geodesic(coords_s, coords_t).km
        
    #print(pairwise_distance, file=sys.stderr)

    """

    p_in = {city['name']: city['population'] / total_population for city in cities}
    p_out = {city['name']: city['population'] / total_population for city in cities}

    traffic_matrix = total_volume_of_traffic * np.outer(list(p_in.values()), list(p_out.values()))
    
    for i, s in enumerate(cities):
        traffic_matrix_dict[s['name']] = dict()
        for j, t in enumerate(cities):
            traffic_matrix_dict[s['name']][t['name']] = traffic_matrix[i][j]

    print(traffic_matrix_dict, file=sys.stderr)

    return traffic_matrix_dict