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

# get the tokens associated with this pool
token0 = dh.getToken0(pool_address=EXAMPLE_POOL)
token1 = dh.getToken1(pool_address=EXAMPLE_POOL)

# get some info (immutables) for this pool
print(dh.getPoolInfo(pool_address=EXAMPLE_POOL))
print(token0)
print(token0.name)

# we can use the same tokens to get other pools (with different fees)
pool500 = dh.getPool(token0_address=token0.address, token1_address=token1.address, fee=500) # 0.05% => 500
pool3000 = dh.getPool(token0_address=token0.address, token1_address=token1.address, fee=3000) # 0.3%
pool10000 = dh.getPool(token0_address=token0.address, token1_address=token1.address, fee=10000) # 1%

print(pool500) # this is a web3.py contract instance
print(pool3000)
print(pool10000)

# we can now interact with the web3 contracts; for example, we can read values from the deployed pool contract, like this:
print(pool500.functions.observe([100]).call()) # see: https://docs.uniswap.org/contracts/v3/reference/core/UniswapV3Pool#observe

# we can also write to the pool if we want to, like deploy liquidity etc. from here (not shown)
