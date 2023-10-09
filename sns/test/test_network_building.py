from sns.network import Network, NodeTypes

class TestNetworkBuilding:

    def test_build_network(self): 
        env, ntwk = Network.from_json('../../topology_builder/results/iridium_static_status.json')

        print(f"\n{env}\n{ntwk}")

        for u, v in ntwk.graph.edges:
            if ntwk.graph.nodes[u]['type'] == NodeTypes.GROUD_STATION:
                assert 'out_port' not in ntwk.graph[u][v].keys()
            else:
                assert 'out_port' in ntwk.graph[u][v].keys()
            
            assert 'wire' in ntwk.graph[u][v].keys()