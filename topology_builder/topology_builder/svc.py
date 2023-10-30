from datetime import datetime
import os
from pathlib import Path
from flask import Flask, Response
from flask import request
import sys
import requests
from topology_builder.builder.min_distance_topology_builder import MinimumDistanceTopologyBuilder
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository

app = Flask(__name__)

BASE_CITY_API_URL = os.environ.get('BASE_CITY_API_URL')
CITY_SVC_API_KEY = Path(os.environ.get('CITY_SVC_API_KEY_FILE')).read_text()
GS_S = []

@app.route("/topology_builder/min_dist_topo_builder/<string:topo_name>")
def hello_world(topo_name: str):
    t = request.args.get('t')
    
    if len(GS_S) == 0:
        cities: str = [city.strip() for city in request.args.get("cities").split(',')]

        for city in cities:
            response = requests.get(
                f"{BASE_CITY_API_URL}?name={city}", headers={"X-Api-Key": CITY_SVC_API_KEY}
            )

            GS_S.append({
                'name' : response.json()[0]['name'],
                'lat' : response.json()[0]['latitude'],
                'lon' : response.json()[0]['longitude'],
            })

    network = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name=topo_name,
                t=datetime.strptime(t, '%Y-%m-%d %H:%M:%S %z'),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            .add_GSs(GS_S)
            .add_ISLs()
            .add_GSLs()
            .build()
        )
    return Response(str(network), mimetype='application/json')

if __name__ == '__main__':
    app.run()
