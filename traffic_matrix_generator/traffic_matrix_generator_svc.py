import json
import os
import pathlib
import sys
from flask import Flask, Response
from flask import request
import requests
import gravity_model.matrix_builder as mxb

app = Flask(__name__)

BASE_CITY_API_URL = os.environ.get('BASE_CITY_API_URL')
CITY_SVC_API_KEY = pathlib.Path(os.environ.get('CITY_SVC_API_KEY_FILE')).read_text()


@app.route("/traffic_matrix")
def traffic_matrix():
    cities: str = [city.strip() for city in request.args.get("cities").split(',')]
    total_volume_of_traffic = float(request.args.get("total_volume_of_traffic"))

    print(cities, file=sys.stderr)

    for i, city in enumerate(cities):
        response = requests.get(
            f"{BASE_CITY_API_URL}?name={city}", headers={"X-Api-Key": CITY_SVC_API_KEY}
        )

        print(response.json(), file=sys.stderr)

        cities[i] = response.json()[0]
    
    traffic_matrix = mxb.build_traffic_matrix(cities=cities, total_volume_of_traffic=total_volume_of_traffic)

    return Response(json.dumps(traffic_matrix, indent=4), mimetype="application/json")


if __name__ == "__main__":
    app.run()
