#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  6 18:00:53 2023

@author: juanpablomadrigalcianci
"""


from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import pandas as pd
import datetime

def get_open_positions(pool_id:str):
    '''
    

    Parameters
    ----------
    pool_id : str
        The address of the pool id.

    Returns
    -------
    pandas dataframe
       Dataframe containing info of each position.

    '''
    
    pool_id=pool_id.lower()
    # GraphQL query to return open positions only (with liquidity > 0)
    position_query = gql("""
    query get_positions($num_skip: Int, $pool_id: ID!) {
      positions(skip: $num_skip, where: {pool: $pool_id, liquidity_gt: 0}) {
        id
        tickLower { tickIdx }
        tickUpper { tickIdx }
        liquidity
        depositedToken0
        depositedToken1
        withdrawnToken0
        withdrawnToken1
        collectedFeesToken0
        collectedFeesToken1
        feeGrowthInside0LastX128
        feeGrowthInside1LastX128
        transaction {
            blockNumber
            timestamp
        }
      }
    }
    """)

    client = Client(
        transport=RequestsHTTPTransport(
            url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            verify=True,
            retries=5,
        )
    )

    # Initialize variables
    positions = []
    num_skip = 0

    # Query and collect data until there's no more
    try:
        while True:
            #print(f"Querying positions, num_skip={num_skip}")
            variables = {"num_skip": num_skip, "pool_id": pool_id}
            response = client.execute(position_query, variable_values=variables)

            if not response.get("positions"):
                break

            num_skip += len(response["positions"])

            for item in response["positions"]:

                
                tick_lower = int(item["tickLower"]["tickIdx"])
                tick_upper = int(item["tickUpper"]["tickIdx"])
                liquidity = int(item["liquidity"])
                deposited0=item["depositedToken0"]
                deposited1=item["depositedToken1"]
                withdrawnToken0=item["withdrawnToken0"]
                withdrawnToken1=item["withdrawnToken1"]
                collectedToken0=item["collectedFeesToken0"]
                collectedToken1=item["collectedFeesToken1"]
                feeGrowthInside0LastX128=int(item['feeGrowthInside0LastX128'])
                feeGrowthInside1LastX128=int(item['feeGrowthInside1LastX128'])
                timestamp = int(item['transaction']['timestamp'])
                time = datetime.datetime.utcfromtimestamp(timestamp)
                block=int(item['transaction']['blockNumber'])
                id = item["id"]  # Keep ID as a string
                positions.append((tick_lower, tick_upper, liquidity, id,
                                  deposited0,deposited1,withdrawnToken0,withdrawnToken1,
                                  collectedToken0,collectedToken1,
                                  feeGrowthInside0LastX128,
                                  feeGrowthInside1LastX128,
                                  time,
                                  block
                                  ))
    except Exception as ex:
        print("An exception occurred while querying position data:", ex)

    # Create DataFrame if there are positions
    if positions:
        df = pd.DataFrame(positions, columns=['lower', 'upper', 'liquidity', 'id',
                                              'deposit0', 'deposit1', 'withdrawn0',
                                              'withdrawn1','collected0','collected1',
                                              'feeGrowthInside0LastX128',
                                              'feeGrowthInside1LastX128',
                                              'time',
                                              'block'
                                              ])
        return df
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no positions were found

# if __name__ == '__main__':
#     pool_id = "0xa6Cc3C2531FdaA6Ae1A3CA84c2855806728693e8"
#     positions_df = get_open_positions(pool_id)
#     print(positions_df)
#     NAME=pool_id+'.csv'
#     positions_df.to_csv(NAME)
