#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  6 18:15:19 2023

@author: juanpablomadrigalcianci
"""

from web3 import Web3
import json
import pandas as pd
import tqdm


MODULUS = 2**256
POSITION_MANAGER_ADDRESS = "0xC36442b4a4522E871399CD717aBDD847Ab11FE88"
BASE=1.0001
NODE='https://mainnet.infura.io/v3/7212153601594b0a9dec007334dc1e77'

def calculate_fa(fg, fo, i, ic):
    """Compute value of 'fa' based on conditions."""
    return fg - fo if i <= ic else fo

def calculate_fb(fg, fo, i, ic):
    """Compute value of 'fb' based on conditions."""
    return fo if i <= ic else fg - fo

def get_pool_and_position_contracts(w3, pool_address, position_manager_address, pool_abi, nft_abi):
    """Initialize contracts for pool and position manager."""
    pool_contract = w3.eth.contract(address=pool_address, abi=pool_abi)
    position_manager_contract = w3.eth.contract(address=position_manager_address, abi=nft_abi)
    return pool_contract, position_manager_contract


def sub256(x, y):
    Q256 = 1 << 256  # Equivalent to 2**256
    ZERO = 0  # Just for clarity in comparison, Python uses 0 directly.
    
    difference = x - y

    if difference < ZERO:
        return (Q256 + difference) % Q256  # Ensure the result is within 0 to 2^256-1
    else:
        return difference

def add256(x, y):
    Q256 = 1 << 256  # Equivalent to 2**256
    MAX_VAL = Q256 - 1  # Maximum value for a 256-bit number
    
    total = x + y  # Calculate the sum

    # If the sum exceeds the max value for a 256-bit number, wrap around
    if total > MAX_VAL:
        return total % Q256
    else:
        return total


def _computefees(position_data: int, 
                 final_block: int,
                 pool: str, 
                 decimals0: int = 6,
                 decimals1: int = 18):
    
    w3 = Web3(Web3.HTTPProvider(NODE))
    try:
        pool=w3.to_checksum_address(pool)
    except:
        pool=w3.toChecksumAddress(pool)
    # Load ABIs
    with open('UniswapV3PoolABI.json', 'r') as abi_file:
        pool_abi = json.load(abi_file)
    with open('position_manager_abi.json', 'r') as abi_file2:
        nft_abi = json.load(abi_file2)

    pool_contract, position_manager_contract = get_pool_and_position_contracts(w3, pool, POSITION_MANAGER_ADDRESS, pool_abi, nft_abi)
    
    # Extracting relevant position data details
    position_id=position_data['id']
    LOWER_TICK = int(position_data['lower'])
    UPPER_TICK = int(position_data['upper'])
    liquidity = float(position_data['liquidity'])
    feeGrowthInside0LastX128 = int(position_data['feeGrowthInside0LastX128'])
    feeGrowthInside1LastX128 = int(position_data['feeGrowthInside1LastX128'])

    #
    initial_block=position_data['block']
    
    # import pdb
    # pdb.set_trace()
    
    slot0_initial = pool_contract.functions.slot0().call(block_identifier=int(initial_block))
    initial_tick = slot0_initial[1]


    # Extract final pool values
    fee_growth_global_0_final = pool_contract.functions.feeGrowthGlobal0X128().call(block_identifier=final_block)
    fee_growth_global_1_final = pool_contract.functions.feeGrowthGlobal1X128().call(block_identifier=final_block)
    tick_info_lower_final = pool_contract.functions.ticks(LOWER_TICK).call(block_identifier=final_block)
    tick_info_upper_final = pool_contract.functions.ticks(UPPER_TICK).call(block_identifier=final_block)
    slot0 = pool_contract.functions.slot0().call(block_identifier=final_block)
    
    current_tick = slot0[1]

    # Compute values for fb and fa
    fb0 = calculate_fb(fee_growth_global_0_final, tick_info_lower_final[2], LOWER_TICK, current_tick)
    fb1 = calculate_fb(fee_growth_global_1_final, tick_info_lower_final[3], LOWER_TICK, current_tick)
    fa0 = calculate_fa(fee_growth_global_0_final, tick_info_upper_final[2], UPPER_TICK, current_tick)
    fa1 = calculate_fa(fee_growth_global_1_final, tick_info_upper_final[3], UPPER_TICK, current_tick)

    # Compute fee differences
    diff0 = add256(fb0 , fa0) 
    diff1 = add256(fb1 , fa1) 
    
    fr0=sub256(fee_growth_global_0_final , diff0)
    fr1=sub256(fee_growth_global_1_final , diff1)

    #fr0 = (fee_growth_global_0_final - diff0) #% MODULUS
    #fr1 = (fee_growth_global_1_final - diff1) #% MODULUS

    # Compute fees in tokens
    fees_token0 = liquidity * sub256(fr0 , feeGrowthInside0LastX128) / 2**128
    fees_token1 = liquidity * sub256(fr1 , feeGrowthInside1LastX128) / 2**128

    p1=BASE**(-current_tick)*10**(decimals1-decimals0)


    # import pdb
    # pdb.set_trace()


    res= {'id':position_id,
        'fees0':fees_token0/10**decimals0,
            'fees1':fees_token1/10**decimals1,
             'price1':p1,
             'initial_price1':BASE**(-initial_tick)*10**(decimals1-decimals0),
             'total_fees_token0':fees_token0/10**decimals0+p1*fees_token1/10**decimals1,
             'tokenIn0':position_data['deposit0'],
             'tokenIn1':position_data['deposit1'],
             'il':LOWER_TICK,
             'iu':UPPER_TICK,
             'ic':current_tick,
             'liquidity':position_data['liquidity'],
             'time':position_data['time'],
             'block':position_data['block']
             }    
    return res




def computeFees(df,decimals0,decimals1,pool,name,final_block):
    res=[]

    for i in tqdm.tqdm(range(len(df))):
        
        try:
            aux=_computefees(position_data=dict(df.iloc[i]), 
                              final_block=final_block,
                              pool=pool, 
                              decimals0=decimals0,
                              decimals1=decimals1)
            res.append(aux)

        except:
            # import pdb
            # pdb.set_trace()
            print(f"skipped position {df.iloc[i]['id']} in "+name)
        


    df=pd.DataFrame(res)
    df.to_csv(name)
    return df
    

