from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from app.config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG


def get_influx_client() -> InfluxDBClient:
    return InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)


def get_write_api():
    return get_influx_client().write_api(write_options=SYNCHRONOUS)
