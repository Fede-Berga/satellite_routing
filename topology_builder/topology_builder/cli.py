import datetime
import json
import os
from pathlib import Path
import sys
import time
import yaml
from typing import Annotated, Optional
import typer
from topology_builder import __app_name__, __version__

sys.path.append(os.path.abspath("./"))
from topology_builder.satellite_repository import STKLeoSatelliteRepository
from topology_builder.topology_builder import (
    MinimumDistanceTopologyBuilder,
    LOSTopologyBuilder,
)

app = typer.Typer()

@app.command()
def build_single_topology(
    config_file: Annotated[str, typer.Option(help="config file.")],
    verbose: Annotated[bool, typer.Option(help="Print logs.")] = False,
) -> None:
    """
    Build the topology associated to a satellite constellation at a certain time instant t.
    """

    with open(config_file, "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
        print("Read config successful")
        print(json.dumps(config, indent=4))

    topology = (
        MinimumDistanceTopologyBuilder(
            verbose=verbose,
            name=config["name"],
            t=datetime.datetime.strptime(config["t"], "%Y-%m-%d %H:%M:%S %z"),
        )
        .add_LEO_constellation(
            STKLeoSatelliteRepository(Path(config["constellation_file"]))
        )
        .add_ISLs()
        .add_GSs(config["ground_stations"])
        .add_GSLs()
        .build()
    )

    typer.secho(f"Topology succeffully built")

    if config["output_file"] == None:
        typer.secho(f"Topology built succeffully")
        typer.secho(topology)
    else:
        with open(config["output_file"], "w") as file:
            topology.dump()
            # json.dump(topology.to_json(), file, indent=4)
            # print(f'Topology successfully saved to "{config["output_file"]}"')


@app.command()
def build_dynamic_topology(
    config_file: Annotated[str, typer.Option(help="config file.")],
    verbose: Annotated[bool, typer.Option(help="Print logs.")] = False,
):
    """
    Build the dynamic topology associated to a satellite constellation.
    """

    with open(config_file, "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
        print("Read config successful")
        print(json.dumps(config, indent=4))

    dt = config["dt"]
    now = start_time = datetime.datetime.strptime(
        config["start_time"], "%Y-%m-%d %H:%M:%S %z"
    )
    end_time = datetime.datetime.strptime(config["end_time"], "%Y-%m-%d %H:%M:%S %z")

    dyn_status = []

    start_time = time.time()

    while now <= end_time:
        if verbose:
            print(f"Building topology at {now}")

        dyn_status.append(
            MinimumDistanceTopologyBuilder(
                verbose=False,
                name=config["name"],
                t=datetime.datetime.strptime(config["t"], "%Y-%m-%d %H:%M:%S %z"),
            )
            .add_LEO_constellation(
                STKLeoSatelliteRepository(Path(config["constellation_file"]))
            )
            .add_ISLs()
            .add_GSs(config["ground_stations"])
            .add_GSLs()
            .build()
        )

        now += datetime.timedelta(milliseconds=dt)

    if verbose:
        print(f"The simulation took {(time.time() - start_time) / 60} minutes")

    with open(config["output_file"], "w") as file:
        json.dump(
            {
                "start_time": start_time,
                "end_time": end_time,
                "dt": dt,
                "topologies": [topology.to_json() for topology in dyn_status],
            },
            file,
            indent=4,
            default=str,
        )
        print(f'\nTopology successfully saved to "{config["output_file"]}"')


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the application's version and exit.",
            is_eager=True,
        ),
    ] = None,
) -> None:
    return
