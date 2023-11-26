#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  9 17:37:53 2023

@author: juanpablomadrigalcianci
"""

import requests
import json


def getNameAndDecimals(POOL_ADDRESS):
    POOL_ADDRESS=POOL_ADDRESS.lower()
    # The Graph endpoint for Uniswap v3
    GRAPH_URL = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    
    # GraphQL query to fetch token names and decimals
    query = """
    {
      pools(where: {id: "POOL_ADDRESS"}) {
        token0 {
          symbol
          decimals
        }
        token1 {
          symbol
          decimals
        }
        feeTier
      }
    }
    """.replace("POOL_ADDRESS", POOL_ADDRESS)
    
    # Perform the POST request to The Graph API
    response = requests.post(GRAPH_URL, json={'query': query})
    data = response.json()
    
    # Parse the response and format the pool name
    if data.get("data", {}).get("pools", []):
        pool = data["data"]["pools"][0]
        token0 = pool["token0"]
        token1 = pool["token1"]
        fee = pool["feeTier"]
        pool_name = f"{token0['symbol']}-{token1['symbol']}-{fee}"
        print(f"Pool Name: {pool_name}")
        print(f"Token 0 ({token0['symbol']}) Decimals: {token0['decimals']}")
        print(f"Token 1 ({token1['symbol']}) Decimals: {token1['decimals']}")
    else:
        print("No pool found with the given address.")
        
    return pool_name,int(token0['decimals']),int(token1['decimals']),token0['symbol'],token1['symbol']
