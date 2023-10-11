from datetime import datetime
import json
import yaml
from pathlib import Path
from flask import Flask, Response
from flask import request, jsonify
from topology_builder.builder.min_distance_topology_builder import MinimumDistanceTopologyBuilder
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository

app = Flask(__name__)

@app.route("/topology_builder/min_dist_topo_builder/<string:topo_name>")
def hello_world(topo_name: str):
    t = request.args.get('t')

    gs_s = [
            {"name": "Tokyo", "lat": 35.652832, "lon": 139.839478},
            {"name": "Melbourne", "lat": -37.840935, "lon": 144.946457},
            {"name": "London", "lat": 51.509865, "lon": -0.118092},
            {"name": "Sao_Paulo", "lat": -23.533773, "lon": -46.625290},
        ]

    network = (
            MinimumDistanceTopologyBuilder(
                verbose=True,
                name=topo_name,
                t=datetime.strptime(t, '%Y-%m-%d %H:%M:%S %z'),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path("./constellations/Iridium_TLE.txt"))
            )
            .add_GSs(gs_s)
            .add_ISLs()
            .add_GSLs()
            .build()
        )
    return Response(str(network), mimetype='application/json')

if __name__ == '__main__':
    app.run()
