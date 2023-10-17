from datetime import datetime, timedelta

import simpy

from sns.network import Network


def run_sns_simulation(
    env: simpy.Environment,
    svc_url: str,
    start_time: datetime,
    end_time: datetime,
    snapshot_duration: timedelta,
) -> None:
    now = start_time
    old_ntwk = None

    while now <= end_time:
        print(f"Building topology at {now}")

        ntwk = Network.from_topology_builder_svc(
            env=env,
            svc_url=f"{svc_url}?t={now.strftime('%Y-%m-%d %H:%M:%S %z').replace('+', '%2B')}&no_gs_s=3",
            old_ntwk=old_ntwk
        )

        #ntwk.nx_plot()
        #print(ntwk)
        #ntwk.dump_routing_info() 

        env.run(until=((now - start_time) + snapshot_duration).seconds)# * 1000)

        #print(f"\n--------- Status at {now} ----------")
        #ntwk.dump_status()

        old_ntwk = ntwk

        now += snapshot_duration
