#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 24 07:48:36 2023

@author: juan
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas
import tqdm
from google.cloud import bigquery
from google.oauth2 import service_account
import matplotlib.dates as mdates
import os


def getGasData(filepath:str='./data/'):
    PATH_TO_KEY="../key.json"
    credentials = service_account.Credentials.from_service_account_file(PATH_TO_KEY)
    client = bigquery.Client(credentials= credentials)
    QUERY='''SELECT timestamp, number,base_fee_per_gas,gas_limit,gas_used,transaction_count FROM `bigquery-public-data.crypto_ethereum.blocks` 
    WHERE DATE(timestamp) > "2021-01-24" '''
    
    filename=filepath+'gasETH.csv'
    
    exists=os.path.exists(filename)
        
    if exists:
        df=pandas.read_csv(filename)

    else:
    
        try:
            df = client.query(QUERY).to_dataframe()
            df=df.sort_values(by='timestamp')
            df.to_csv(filepath+'gasETH.csv')
            print('🟢 Done!')
        except:
            print('🟠 There was an issue querying the data!')
            df=None
    return df