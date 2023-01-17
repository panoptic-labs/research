#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 07:53:24 2023

@author: juan
"""



import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import urllib.request
import json
import os
START='2021-06-01'

#%% Get pool names

SHEET_ID = '1aGYcW5W1yE7rvEPDf-pS8BeA2M1PTx4FrPWrDKHPFVA'
SHEET_NAME = 'top10TVLjan10_23'
url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
pools=pd.read_csv(url)
pools

stable=[]

def dataDownload(poolAddress:str,filePath:str,all=True):
    
    filepath=filePath+poolAddress+'.csv'
    if os.path.isfile(filepath):
        print('file already in path, skipping')
        return
    else:
        print('Downloading csv file...')
        df = pd.read_gbq(f"SELECT * FROM `arcane-world-371019.First_sync.1` WHERE address=lower('{poolAddress}') {'' if all else 'LIMIT 1000'}", project_id="arcane-world-371019", progress_bar_type='tqdm')
        df.to_csv(filepath, index=False)
        print(f"✍ Data written to: {filepath}")
        return

def getAvgPrice(df,start,name,window):

    df=df[df['time']>start]
    df=df.resample(window, on='time')['price'].pad()
    df = df.interpolate(limit_direction='backward')

    df=df.dropna()
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
         'name':pool['token0']['symbol']+'-'+pool['token1']['symbol']+'-'+pool['feeTier']}
    
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
    
    
    if res['token1']=='USDC':
    
        df['price'] = 1.0001**df['tick']*10**(token0Decimals-token1Decimals)
    else:
        df['price'] = 1/(1.0001**df['tick']*10**(token0Decimals-token1Decimals))
    
    
    import pdb
    pdb.set_trace()
    
    res['price']= getAvgPrice(df,start,res['name'],window)


    
    return res

def mergeDf(dfList,col='time'):
    
    N=len(dfList)
    
    data=dfList[0]
    
    
    for i in range(1,N):
        
        
        data=pd.merge(data, dfList[i],on=col)
    
    return data

results=[]
dfs=[]

for i in range(len(pools)):
    p=pools['address'].iloc[i]
    n=pools['name'].iloc[i]
    print('building info for '+n+'...')
    aux=getPoolInfo(p, start=START)
    results.append(aux)
    dfs.append(aux['price'])


merged=mergeDf(dfs)
#%%
plt.style.use('../../stylesheet/panoptic-dark-16:9.mplstyle')
merged.plot()
plt.title('Price for different stablecoin pools')
plt.ylim([0.99,1.02])

# import seaborn as sns

# sns.pairplot(merged)
plt.show()


#%%

cols=list(merged.columns)

for c in cols:
    plt.hist(merged[c],bins=20,alpha=0.6,label=c, density=True)
plt.legend()
plt.title('Histogram of price')
plt.xlabel('Price')
plt.ylabel('Density')
plt.xlim([0.995,1.01])
plt.show()
# #%%
#%%
print(merged.describe())


import seaborn as sns
corr = merged.corr()
corr.style.background_gradient(cmap='BuPu')
sns.heatmap(corr, cmap="BuPu",annot=True,annot_kws={"size":6})
plt.title('Correlation matrix, stablecoin pools')
plt.show()
# #%%

# names=['FRAX-USDC', 'USDC-ETH']

# df=get_price(df,token0Digits=18,token1Digits=18)
# df2=get_price(df2,token0Digits=18,token1Digits=18,inv=True)

# a1=getAvgPrice(df,START,names[0])
# a2=getAvgPrice(df2,START,names[1])

# data=mergeDf([a1,a2],names,col='time')
