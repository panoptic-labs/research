#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains a function to compute the estimated annual volatility of an asset.

Created on Tue Nov 7 17:55:38 2023
@author: juanpablomadrigalcianci
"""

import numpy as np
import pandas as pd
from pandas import Series, DataFrame
import yfinance as yf


def compute_volatility(date: pd.Timestamp, 
                       price0: Series, 
                       price1: Series, 
                       lookback: int = 120) -> float:
    """
    Compute the estimated annual volatility of an asset.

    Parameters:
    current_date (pd.Timestamp): The date for which the volatility is computed.
    price0 (Series): Series of prices at the beginning of the period.
    price1 (Series): Series of prices at the end of the period.
    lookback (int, optional): Number of days to look back for volatility computation. Default is 90.

    Returns:
    float: The annualized volatility of the asset.
    """
    
    # Filter the price series to include only dates before the current date
    p0 = price0[price0.index <= date]
    p1 = price1[price1.index <= date]
    
    # Calculate the ratio of price1 to price0
    p10 = p1 / p0
    
    # Take the most recent 'lookback' period
    p10 = p10[-lookback:]
    
    # Calculate daily returns and drop the first NaN value
    p10 = p10.pct_change().dropna()
    
    # Calculate daily volatility (standard deviation of daily returns)
    daily_volatility = p10.std()
    
    # Assuming there are 252 trading days in a year for the annualization factor
    trading_days = 365
    
    # Annualize the daily volatility
    annual_volatility = daily_volatility * np.sqrt(trading_days)
    # import pdb
    # pdb.set_trace()
    return annual_volatility

# df=pd.read_csv('position_info.csv')
# price1=yf.download('ETH-USD')['Close']
# price0=price1.apply(lambda x: 1)
# aux=[compute_volatility(df.iloc[i][-1], price0, price1) for i in range(len(df))]
# df['vol']=aux
# df.to_csv('position_info.csv')