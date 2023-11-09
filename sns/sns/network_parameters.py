class NetworkParameters:
    LEO_GEO_GS_TD = 0.35 # seconds
    PACKET_SIZE = 1_500  # bytes
    SATELLITE_QUEUE_SIZE = PACKET_SIZE * 10_000 # bytes
    TOTAL_VOLUME_OF_TRAFFIC = 500_000_000 # bytes / second
    CITIES_FILE_PATH = '../cities.yaml'
    SATELLITE_PORT_RATE = 1_000_000_000  # bit / second
    LINK_SWITCH_DELAY = 0.1  # seconds
    LIMIT_BYTES = True
    ALPHA = 0.125