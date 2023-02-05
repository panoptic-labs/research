#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 08:56:07 2023

@author: juan
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import urllib.request
import json
import os

plt.style.use('../../stylesheet/panoptic-dark-16:9.mplstyle')


def get_twos_comp(hex_str, bits: int=256):
    """Calculate two's complement"""
    num = int(hex_str, 16)
    if (num & (1 << (bits - 1))) != 0: # Check if first bit is set
        num = num - (1 << bits)        # Get two's complement
    return num

def dataDownload(poolAddress:str,filePath:str,gbqTable:str,gbqProject:str,all:bool=True):
    
    filename=filePath+poolAddress+'.csv'
    if os.path.isfile(filename):
        print('file already in path, skipping')
        return
    else:
        os.system('mkdir '+str(filePath))
        print('Downloading csv file...')
        df = pd.read_gbq(f"SELECT * FROM '{gbqTable}' WHERE address=lower('{poolAddress}') {'' if all else 'LIMIT 1000'}", project_id="{gbqProject}", progress_bar_type='tqdm')
        df.to_csv(filename, index=False)
        print(f"✍ Data written to: {filename}")
        return

def getAvgPrice(df,start,name,window):

    

    df=df[df['time']>start]
    df=df.set_index('time')
    df=df.resample(window)['price'].mean()
    df=df.interpolate(method='time')
    
    df=df.rename(name)
    return df


def getPoolInfo(poolID:str,start,dataDir='../../.data/',window='1H'):
    
    poolID=poolID.lower()
    URL = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"

    query = """query pools($pool_id: ID!) {
      pools (where: {id: $pool_id}) {
        tick
        liquidity
        feeTier
        totalValueLockedUSD
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
    req = urllib.request.Request(URL)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    jsondata = {"query": query, "variables": {"pool_id": poolID}}
    jsondataasbytes = json.dumps(jsondata).encode('utf-8')
    req.add_header('Content-Length', len(jsondataasbytes))
    response = urllib.request.urlopen(req, jsondataasbytes)
    obj = json.load(response)
        
    
    
    pool = obj['data']['pools'][0]
    

    res={'poolId':poolID,
         'tier':pool['feeTier'],
         'token0':pool['token0']['symbol'],
         'token0Decimals':np.float64(pool['token0']['decimals']),
         'token1':pool['token1']['symbol'],
         'token1Decimals':np.float64(pool['token1']['decimals']),
         'tvl':np.float64(pool['totalValueLockedUSD']),
         'name':pool['token0']['symbol']+'-'+pool['token1']['symbol']+'-'+str(int(pool['feeTier'])/10000)+'%'}
    
    try:
        df=pd.read_csv(dataDir+poolID+'.csv')
    except:
        print('pool not found, downloading!')
        dataDownload(poolAddress=poolID,filePath=dataDir,all=True)
        df=pd.read_csv(dataDir+poolID+'.csv')

    
    df['time']=df['block_timestamp']
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df=df.sort_values(by='time')
    
    token0Decimals=res['token0Decimals']
    token1Decimals=res['token1Decimals']
    
    #token1 is the numeraire
    


    df['amount0']=df['amount0'].apply(get_twos_comp)/ (10 ** token0Decimals)
    df['amount1']=df['amount1'].apply(get_twos_comp)/ (10 ** token1Decimals)
    
    res['df']=df
    
    if res['token1']=='WETH':
    
        df['price'] = 1.0001**df['tick']*10**(token0Decimals-token1Decimals)
        df['flow']=df['amount1'].apply(lambda x: np.abs(x))

    
    else:
        df['price'] = 1/(1.0001**df['tick']*10**(token0Decimals-token1Decimals))
        df['flow']=df['amount0'].apply(lambda x: np.abs(x))
    
    df=df.dropna()

    #df['price']= getAvgPrice(df,start,res['name'],window='1H')

    return res


def getPoolsOneHour(start):

    POOLS=[
           '0x1d42064Fc4Beb5F8aAF85F4617AE8b3b5B8Bd801',
           '0xCBCdF9626bC03E24f779434178A73a0B4bad62eD',
           '0x7379e81228514a1D2a6Cf7559203998E20598346',
           '0x290A6a7460B308ee3F19023D2D00dE604bcf5B42',
           '0xa3f558aebAecAf0e11cA4b2199cC5Ed341edfd74',
           '0x2F62f2B4c5fcd7570a709DeC05D68EA19c82A9ec',
           '0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8',
            '0x82c427AdFDf2d245Ec51D8046b41c4ee87F0d29C'
           ]
    
    for p in POOLS:
        info=getPoolInfo(poolID=p,start=start,dataDir='../../.data/')
        df=info['df']
        df=df[df['time']>=START]
        df = df.set_index('time') 
        df=df.dropna()
        dfp=df.price.resample('1H').mean()
        dfp=dfp.rename_axis(index='Date')#%%
        #dfp.index=dfp.index.strftime('%Y-%m-%d %H:%M:%S')
        dfp=dfp.rename(info['name'])
        dfp.to_csv('./Data/'+str(info['name'])+'.csv')
        


START='2021-06-01'
getPoolsOneHour(start=START)    
    
    
