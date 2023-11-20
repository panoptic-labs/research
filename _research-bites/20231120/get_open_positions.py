#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  6 11:25:36 2023

@author: juan
"""


from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import pandas as pd
import datetime



def get_open_positions(pool_id):
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
            print(f"Querying positions, num_skip={num_skip}")
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
                time=datetime.datetime.utcfromtimestamp(item['transaction']['timestamp'])
                block=int(item['transaction']['blockNumber'])

                id = item["id"]  # Keep ID as a string
                positions.append((tick_lower, tick_upper, liquidity, id,
                                  deposited0,deposited1,withdrawnToken0,withdrawnToken1,
                                  collectedToken0,collectedToken1,time,block))
    except Exception as ex:
        print("An exception occurred while querying position data:", ex)

    # Create DataFrame if there are positions
    if positions:
        df = pd.DataFrame(positions, columns=['lower', 'upper', 'liquidity', 'id','deposit0','deposit1','withdrawn0','withdrawn1','collected0','collected1'])
        return df
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no positions were found

if __name__ == '__main__':
    pool_id = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    positions_df = get_open_positions(pool_id)
    print(positions_df)

