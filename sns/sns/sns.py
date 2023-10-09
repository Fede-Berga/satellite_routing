from datetime import datetime, timedelta

import simpy

from sns.network import Network


class Sns:
    def __init__(
        self, env: simpy.Environment, start_time: datetime, end_time: datetime, snapshot_duration: timedelta
    ) -> None:
        self.env = env
        self.start_time = start_time
        self.end_time = end_time
        self.snapshot_duration = snapshot_duration
    
    def run(self, svc_url: str) -> None:

        now = self.start_time

        while now <= self.end_time:

            ntwk = Network.from_topology_builder_svc(svc_url)

            self.env.run(self.snapshot_duration)

            now += self.snapshot_duration
