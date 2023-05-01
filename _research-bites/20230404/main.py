#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 30 08:20:09 2023

@author: juanpablomadrigalcianci
"""

#!/usr/bin/env python3

#
# Example that shows the full range of the current liquidity distribution
# in the 0.3% USDC/ETH pool using data from the Uniswap v3 subgraph.
#

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import math
import sys
import pandas as pd
import numpy as np
# default pool id is the 0.3% USDC/ETH pool
POOL_ID = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"

# if passed in command line, use an alternative pool ID
if len(sys.argv) > 1:
    POOL_ID = sys.argv[1]

TICK_BASE = 1.0001

pool_query = """query get_pools($pool_id: ID!) {
  pools(where: {id: $pool_id}) {
    tick
    sqrtPrice
    liquidity
    feeTier
    volumeToken0
    volumeToken1
    token0 {
      symbol
      decimals
    }
    token1 {
      symbol
      decimals
    }
  }
}"""

tick_query = """query get_ticks($num_skip: Int, $pool_id: ID!) {
  ticks(skip: $num_skip, where: {pool: $pool_id}) {
    tickIdx
    liquidityNet
  }
}"""


def tick_to_price(tick):
    return TICK_BASE ** tick

# Not all ticks can be initialized. Tick spacing is determined by the pool's fee tier.
def fee_tier_to_tick_spacing(fee_tier):
    return {
        100: 1,
        500: 10,
        3000: 60,
        10000: 200
    }.get(fee_tier, 60)


client = Client(
    transport=RequestsHTTPTransport(
        url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
        verify=True,
        retries=5,
    ))

# get pool info
try:
    variables = {"pool_id": POOL_ID}
    response = client.execute(gql(pool_query), variable_values=variables)

    if len(response['pools']) == 0:
        print("pool not found")
        exit(-1)

    pool = response['pools'][0]
    current_tick = int(pool["tick"])
    tick_spacing = fee_tier_to_tick_spacing(int(pool["feeTier"]))

    token0 = pool["token0"]["symbol"]
    token1 = pool["token1"]["symbol"]
    decimals0 = int(pool["token0"]["decimals"])
    decimals1 = int(pool["token1"]["decimals"])
except Exception as ex:
    print("got exception while querying pool data:", ex)
    exit(-1)
#%%
# get tick info
tick_mapping = {}
num_skip = 0
try:
    while True:
        print("Querying ticks, num_skip={}".format(num_skip))
        variables = {"num_skip": num_skip, "pool_id": POOL_ID}
        response = client.execute(gql(tick_query), variable_values=variables)
        if len(response["ticks"]) == 0:
            break
        num_skip += len(response["ticks"])
        for item in response["ticks"]:
            tick_mapping[int(item["tickIdx"])] = int(item["liquidityNet"])
except Exception as ex:
    print("got exception while querying tick data:", ex)
    exit(-1)





    #%%

def get_price_and_liq():

    # Start from zero; if we were iterating from the current tick, would start from the pool's total liquidity
    liquidity = 0
    
    # Find the boundaries of the price range
    min_tick = min(tick_mapping.keys())
    max_tick = max(tick_mapping.keys())
    
    # Compute the tick range. This code would work as well in Python: `current_tick // tick_spacing * tick_spacing`
    # However, using floor() is more portable.
    current_range_bottom_tick = math.floor(current_tick / tick_spacing) * tick_spacing
    
    current_price = tick_to_price(current_tick)
    adjusted_current_price = current_price / (10 ** (decimals1 - decimals0))
    
    # Sum up all tokens in the pool
    total_amount0 = 0
    total_amount1 = 0
    L=[]
    
    # Guess the preferred way to display the price;
    # try to print most assets in terms of USD;
    # if that fails, try to use the price value that's above 1.0 when adjusted for decimals.
    stablecoins = ["USDC", "DAI", "USDT", "TUSD", "LUSD", "BUSD", "GUSD", "UST"]
    if token0 in stablecoins and token1 not in stablecoins:
        invert_price = True
    elif adjusted_current_price < 1.0:
        invert_price = True
    else:
        invert_price = False
    
    # Iterate over the tick map starting from the bottom
    tick = min_tick
    ticks=[]
    while tick <= max_tick:
        liquidity_delta = tick_mapping.get(tick, 0)
        liquidity += liquidity_delta
    
        price = tick_to_price(tick)
        adjusted_price = price / (10 ** (decimals1 - decimals0))
        if invert_price:
            adjusted_price = 1 / adjusted_price
            tokens = "{} for {}".format(token0, token1)
        else:
            tokens = "{} for {}".format(token1, token0)
    
        should_print_tick = liquidity != 0
        #if should_print_tick:
           # print("ticks=[{}, {}], bottom tick price={:.6f} {}".format(tick, tick + tick_spacing, adjusted_price, tokens))
    
        # Compute square roots of prices corresponding to the bottom and top ticks
        bottom_tick = tick
        top_tick = bottom_tick + tick_spacing
        sa = tick_to_price(bottom_tick // 2)
        sb = tick_to_price(top_tick // 2)
    
        if tick < current_range_bottom_tick:
            # Compute the amounts of tokens potentially in the range
            amount1 = liquidity * (sb - sa)
            amount0 = amount1 / (sb * sa)
    
            # Only token1 locked
            total_amount1 += amount1
    
            if should_print_tick:
                adjusted_amount0 = amount0 / (10 ** decimals0)
                adjusted_amount1 = amount1 / (10 ** decimals1)
                cp=1 / adjusted_current_price if invert_price else adjusted_current_price
                print('current price')
                print(cp)
                #print("        {:.2f} {} locked, potentially worth {:.2f} {}".format(adjusted_amount1, token1, adjusted_amount0, token0))
                L.append(adjusted_amount1*cp)
        elif tick == current_range_bottom_tick:
            # Always print the current tick. It normally has both assets locked
            # Print the real amounts of the two assets needed to be swapped to move out of the current tick range
            current_sqrt_price = tick_to_price(current_tick / 2)
            amount0actual = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
            amount1actual = liquidity * (current_sqrt_price - sa)
            adjusted_amount0actual = amount0actual / (10 ** decimals0)
            adjusted_amount1actual = amount1actual / (10 ** decimals1)
            L.append(adjusted_amount1actual*cp+adjusted_amount0actual)
    
            total_amount0 += amount0actual
            total_amount1 += amount1actual
     

    
    
        else:
            # Compute the amounts of tokens potentially in the range
            amount1 = liquidity * (sb - sa)
            amount0 = amount1 / (sb * sa)
    
            # Only token0 locked
            total_amount0 += amount0
    
            if should_print_tick:
                adjusted_amount0 = amount0 / (10 ** decimals0)
                adjusted_amount1 = amount1 / (10 ** decimals1)
                L.append(adjusted_amount0)
                #print("        {:.2f} {} locked, potentially worth {:.2f} {}".format(adjusted_amount0, token0, adjusted_amount1, token1))
        ticks.append(tick)
        tick += tick_spacing
    

    price=1/(1.0001**np.array(ticks)*1e-12)
    
    return price,np.array(L)
#%%
price,L=get_price_and_liq()
#%%

import matplotlib.pyplot as plt
plt.style.use('panoptic-dark-16_9.mplstyle')
VOL=8e6
current_price=1/(1.0001**current_tick*10**(decimals0-decimals1))
lp=L[price[:-1]<1e4]
pp=price[price<1e4]
IV=2*0.3/100*(VOL/lp)**0.5*(365)**0.5


fig, ax1 = plt.subplots()

ax1.stairs(lp/1e6,pp,label='Value locked (in USDC)')
ax1.set_xlim([500,5000])
plt.ylim([0,1.25])
ax1.set_xlabel('ETH price')
ax1.set_ylabel('USDC (millions)')
ax1.vlines(current_price,0,np.max(lp)/1e6,label='Current price, {} (USDC)'.format(round(current_price,2)),color='C1')
ax1.legend()
ax1.set_title('Value Locked & Volatility Smile, ETH-USDC-0.3%')


ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
color='C2'
ax2.set_ylabel('Implied Volatility (%)', color=color)  # we already handled the x-label with ax1
ax2.plot(pp[:-1],IV*100*20, color=color)
ax2.tick_params(axis='y', labelcolor=color)
ax2.set_ylim([0,75])
fig.tight_layout()  # otherwise the right y-label is slightly clipped
plt.show()




#%%


   
