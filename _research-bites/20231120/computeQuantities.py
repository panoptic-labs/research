#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 09:37:04 2023

@author: juan
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 08:29:38 2023
@author: juan
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import yfinance as yf
import scipy.stats as stats
from datetime import datetime
from get_pool_name_and_decimals import getNameAndDecimals
from computeVolatility import compute_volatility
from blackScholes import black_scholes_call_option
from get_pool_data import get_open_positions
from compute_data import computeFees
TICK_BASE=1.0001
FINAL_DATE='2023-11-06'


def compute_prices(df, decimals0, decimals1):
    TICK_BASE = 1.0001
    df['pb'] = TICK_BASE ** -df['il'] * 10 ** (decimals1 - decimals0)
    df['pa'] = TICK_BASE ** -df['iu'] * 10 ** (decimals1 - decimals0)
    return df

def download_prices(token):
    return yf.download(token + '-USD')['Close']

def getVolatilities(df, p0, p1):
    df['vol']=[compute_volatility(df.iloc[i]['time'],p0,p1) for i in range(len(df))]
    return df
    

def getBSParams(df,p0,final_date=FINAL_DATE):
    p=p0[p0.index<final_date]
    p=p.iloc[-1]
    df['total_fees_usd']=p*df['total_fees_token0']
    # computes the dtes
    r=(df['pb']/df['pa'])**0.5
    sr=r**0.5
    df['Tr']=365*2*np.pi*((sr-1)/(sr+1))**2/df['vol']**2
    df['K']=(df['pb']*df['pa'])**0.5
    df['S']=df['initial_price1']
    return df

def getBSPremia(df,r:float=0.0):
    
    df['bs_premia']=[black_scholes_call_option(S=df['S'].iloc[i],
                                   K=df['S'].iloc[i],
                                   T=df['Tr'].iloc[i]/365,
                                   r=0.0,
                                   sigma=df['vol'].iloc[i]) for i in range(len(df))]
    return df

def _getPrices(t0,t1):
    price0=download_prices(t0)
    price1=download_prices(t1)
    return price0,price1


def tick_to_price(tick):
    TICK_BASE = 1.0001
    return TICK_BASE ** tick

def getAmounts(df, decimals0, decimals1, price0, price1, final_date=FINAL_DATE):
    

    def calculate_amounts(row):
        sa = tick_to_price(row['il'] / 2)
        sb = tick_to_price(row['iu'] / 2)
        current_sqrt_price = tick_to_price(row['ic'] / 2)
        liquidity = int(row['liquidity'])
        if row['iu'] <= row['ic']:  # Only token1 locked
            amount0, amount1 = 0, liquidity * (sb - sa)
        elif row['il'] < row['ic'] < row['iu']:  # Both tokens present
            amount0 = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
            amount1 = liquidity * (current_sqrt_price - sa)
        else:  # Only token0 locked
            amount0, amount1 = liquidity * (sb - sa) / (sa * sb), 0

        adjusted_amount0 = amount0 / (10 ** decimals0)
        adjusted_amount1 = amount1 / (10 ** decimals1)

        p1 = price1[price1.index <= row['time']].iloc[-1]
        p0 = price0[price0.index <= row['time']].iloc[-1]
        p1f = price1[price1.index <= final_date].iloc[-1]
        p0f = price0[price0.index <= final_date].iloc[-1]

        return adjusted_amount0, adjusted_amount1, p0, p1, p0f, p1f

    results = df.apply(calculate_amounts, axis=1, result_type='expand')
    df[['token1Out', 'token0Out', 'initialPrice0', 'initialPrice1', 'finalPrice0', 'finalPrice1']] = results
    return df


def getFinalValues(df,r_trunc,final_date=FINAL_DATE):
    df['r'] = (df['pb'] / df['pa']) ** 0.5
    df=df[df['r']<r_trunc]
    df['principal'] = df['initialPrice0'] * df['tokenIn0'] + df['initialPrice1'] * df['tokenIn1']
    p = df['total_fees_usd'].iloc[0] / df['total_fees_token0'].iloc[0]
    df['number_of_contracts'] = df['principal'] / df['initialPrice1']
    df['finalPositionValue'] = p * df['token0Out'] + df['price1'] * p * df['token1Out']
    date1 = datetime.strptime(final_date, "%Y-%m-%d")
    df['daysOpen'] = (date1 - pd.to_datetime(df['time'])).dt.total_seconds() / 86400
    df['yearsOpen'] = df['daysOpen'] / 365
    df['adj_premia'] = df['bs_premia'] * df['number_of_contracts'] * df['initialPrice0']
    
   
    
    df['ratio'] = df['adj_premia'] / df['total_fees_usd']
    df = df[(df['adj_premia'] > 1e-1) & (df['adj_premia'] < 1e10) & (df['daysOpen'] > 0)]

    return df




def computeQuantities(pool_id,df=None,r_trunc=6,final_date=FINAL_DATE,final_block=18516134):
    print('getting pool info...')
    name,decimals0,decimals1,t0,t1=getNameAndDecimals(pool_id)
    if df is None:
        try:
            df=pd.read_csv(name+'.csv')
        except:
            print(f'Downloading pool data for {name} ...')
            positions_df = get_open_positions(pool_id)
            #positions_df=positions_df.iloc[:5]
            print('Done!')
            print('')
            print(f'Computing pool fees for {name} ...')
            df=computeFees(positions_df,decimals0,decimals1,pool_id,name,final_block)
            df.to_csv(name+'.csv')
    price0,price1=_getPrices(t0, t1)
    df=compute_prices(df, decimals0, decimals1)
    print('getting volatilities...')
    df=getVolatilities(df, price0, price1)
    print('getting BS params and premia...')

    df=getBSParams(df, price0)
    df=getBSPremia(df,price0)

    print('getting Final values...')

    df=getAmounts(df,decimals0,decimals1,price0,price1,final_date=final_date)
    df=getFinalValues(df,  r_trunc, FINAL_DATE)
    print('Done!')
    #df.to_csv(name+'.csv')

    return df,name
    
