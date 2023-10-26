from datetime import datetime, timedelta
import simpy
from sns.sns import run_sns_simulation
import pytz


class TestSns:

    def test_sns(self):

        print('\n')

        run_sns_simulation(
            env=simpy.Environment(),
            svc_url="http://localhost:8000/topology_builder/min_dist_topo_builder/iridium",
            start_time=datetime(year=2023, month=9, day=12, hour=10, minute=0, second=0, tzinfo=pytz.UTC),
            end_time=datetime(year=2023, month=9, day=12, hour=10, minute=10, second=0, tzinfo=pytz.UTC),
            snapshot_duration=timedelta(seconds=1)
        )