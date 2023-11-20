#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  9 17:46:46 2023

@author: juanpablomadrigalcianci
"""

from scipy.stats import norm
import math

def black_scholes_call_option(S, K, T, r, sigma):
    """
    Calculate the price of a European call option using the Black-Scholes model.
    
    Parameters:
    S (float): Current price of the underlying asset (e.g., stock).
    K (float): Strike price of the option.
    T (float): Time to expiration in years.
    r (float): Risk-free interest rate (annual).
    sigma (float): Volatility of the underlying asset (annual).

    Returns:
    float: Price of the call option.
    """
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    N_d1 = 0.5 * (1 + math.erf(-d1 / math.sqrt(2)))
    N_d2 = 0.5 * (1 + math.erf(-d2 / math.sqrt(2)))

    call_price = - S * N_d1 + K * math.exp(-r * T) * N_d2
    return call_price