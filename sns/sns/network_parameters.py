class NetworkParameters:
    LEO_GEO_GS_TD = 0.35 # seconds
    SATELLITE_QUEUE_SIZE = 250_000_000 #bytes
    PACKET_SIZE = 1_500  # bytes
    TOTAL_VOLUME_OF_TRAFFIC = 2_500_000_000_000 # bytes / second
    CITIES_FILE_PATH = '../cities.yaml'
    SATELLITE_PORT_RATE = 1_000_000_000  # bytes / second
    LINK_SWITCH_DELAY = 0.1  # seconds
    LIMIT_BYTES = True