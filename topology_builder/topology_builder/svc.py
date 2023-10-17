from datetime import datetime
from pathlib import Path
from flask import Flask, Response
from flask import request
import yaml
from topology_builder.builder.min_distance_topology_builder import MinimumDistanceTopologyBuilder
from topology_builder.repository.satellite_repository import STKLeoSatelliteRepository

app = Flask(__name__)

@app.route("/topology_builder/min_dist_topo_builder/<string:topo_name>")
def hello_world(topo_name: str):
    t = request.args.get('t')
    no_gs_s = int(request.args.get('no_gs_s'))
    config_file = 'config.yaml'

    with open(config_file, "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
    
    gs_s = config["ground_stations"][:no_gs_s]

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
