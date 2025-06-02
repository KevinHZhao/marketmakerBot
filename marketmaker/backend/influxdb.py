import os

from dotenv import load_dotenv
from influxdb import InfluxDBClient
import matplotlib as mpl
from matplotlib import pyplot as plt
from io import BytesIO
import pytz
import pandas as pd
from datetime import datetime, timedelta
mpl.use("agg")

load_dotenv(override = True)

client = InfluxDBClient(
    host = "baultbunters.duckdns.org",
    port = 8086,
    username = os.getenv("IDB_USER"),
    password = os.getenv("IDB_PASS"),
    database = "GTNH"
)

def query_item(item: str):
    """
    Query the InfluxDB for a specific item.
    """
    query = f"SELECT * FROM items WHERE item = '{item}' AND time >= now() - 4h"
    results = client.query(query)
    return list(results.get_points())

def query_fluid(fluid: str):
    """
    Query the InfluxDB for a specific fluid.
    """
    query = f"SELECT * FROM fluids WHERE fluid = '{fluid}' AND time >= now() - 4h"
    results = client.query(query)
    return list(results.get_points())

def plotter(results, item: str):
    """
    Plot the results from the InfluxDB query.
    """
    df = pd.DataFrame(results)
    df['time'] = pd.to_datetime(df['time'], utc = True)
    df['time'] = df['time'].dt.tz_convert('US/Eastern')
    df.set_index('time', inplace=True)

    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df['amount'], marker='o', linestyle='-', markersize = 1.5)
    plt.title(f'{item} Amount (Last 4 Hours)')
    plt.xlabel('Time')
    plt.ylabel('Amount')
    plt.grid()
    
    # Save the plot to a BytesIO object
    img_buffer = BytesIO()
    plt.savefig(img_buffer)
    img_buffer.seek(0)
    
    return img_buffer

results = client.query("SHOW MEASUREMENTS")
print(list(results.get_points()))

