#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  5 09:11:09 2023

@author: juan
"""

from pools import getPoolsOneHour
import pandas as pd
import os
import glob
import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('../../stylesheet/panoptic-dark-16:9.mplstyle')
#%% Downloads pools 
START='2021-06-01'
getPoolsOneHour(start=START)    



#%% Here we create a dataframe with the hourly data in USDC



# use glob to get all the csv files 
# in the folder
path = './Data/'
files = glob.glob(os.path.join(path, "*.csv"))

dfs=[]

for f in files:
    aux=pd.read_csv(f)
    aux=aux.set_index('Date')
    
    #aux=aux.rename(f[7:-5])
    dfs.append(aux)
  
data=pd.DataFrame(dfs[0])

for i in range(1,len(dfs)):
    data=pd.concat([data,dfs[i]],axis=1)

data=data.dropna()

usdc_price=1/(data['USDC-WETH-0.3%'].values)

for c in data.columns:
    data[c]=data[c]*usdc_price


data['USDC-WETH-0.3%']=usdc_price


#%% Here we compute the log returns 
lr=np.log(data/data.shift(1)).dropna()
time=pd.to_datetime(lr.index).values
lr.columns=['LDO', 'UNI', 'oSQTH', 'WBTC',
       'APE', 'MATIC', 'SHIB', 'USDC',
       'sETH2']
for c in lr.columns:
    plt.hist(lr[c],bins=40,histtype='step',label=c)
plt.xlim([-0.5,0.5])
plt.legend()
plt.show()

volUSDC=lr['USDC'].std()
vols=lr.std()

betas={}

for c in lr.columns:
    
    voli=lr[c].std()
    rho=np.corrcoef(lr[c].values,lr['USDC'].values)
    betas[c]=round(rho[0,1]*voli/volUSDC,3)
    
#%% Plot the results

lr=lr.drop(columns='USDC')
sns.heatmap(lr.corr(),annot=True,annot_kws={"size":5})
sns.set(font_scale=0.75)
plt.title('Price correlation matrix')



