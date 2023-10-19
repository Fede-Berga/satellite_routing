from ns.switch.switch import SimplePacketSwitch
import simpy


class LeoSatellite:
    def __init__(
        self,
        env: simpy.Environment,
        switch: SimplePacketSwitch,
        setup_delay: float = 0,
        #link_switch_delay: Dict[int, float],
    ) -> None:
        self.env = env
        self.switch = switch
        self.setup_delay = setup_delay
        #self.link_switch_delay = link_switch_delay
        self.action = env.process(self.run())
        self.store = simpy.Store(env)

    def run(self):
        print(f'waiting delay setup at {self.env.now}')
        yield self.env.timeout(self.setup_delay)
        print(f'waiting is over at {self.env.now}')
        while True:
            packet = yield self.store.get()
            self.switch.put(packet)

    def put(self, packet):
        return self.store.put(packet)
