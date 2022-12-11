"""
Sync data to local disk.

Use with `force=True` to force a re-download of all data in the BigQuery Table.
When `force=False` the data is not download if it exists under the data path (default: `./data/data.csv`)

@author Axicon Labs Inc.
"""
from research import DataHandler

EXAMPLE_POOL = "0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c"

dh = DataHandler()
df = dh.download(pool_address=EXAMPLE_POOL, all=True, force=False)

token0 = dh.getToken0(pool_address=EXAMPLE_POOL)
print(token0)
print(token0.name)
