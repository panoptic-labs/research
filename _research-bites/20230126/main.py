#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 24 07:44:15 2023

@author: juan
"""
"""
Created on Tue Jan 24 07:44:15 2023

@author: juan
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas
import tqdm
from google.cloud import bigquery
from google.oauth2 import service_account
import matplotlib.dates as mdates
from getGasData import getGasData
import matplotlib.dates as mdates
plt.style.use('../../stylesheet/panoptic-dark-16:9.mplstyle')


# gets and cleans gas dataset


gas=getGasData()
gas['timestamp']= pandas.to_datetime(gas['timestamp'], utc=True)
gas['dt']=gas['timestamp'].diff()/ np.timedelta64(1, 's')
gas=gas.sort_values(by='number')
EIP_BLOCK=12965000
MERGE_BLOCK=15537393
pre=gas[gas['number']>EIP_BLOCK]
pre=pre[pre['number']<MERGE_BLOCK]
merge=gas[gas['number']>MERGE_BLOCK]

gas['regime']=['pre-merge']*len(gas)
indx=gas[gas['number']>MERGE_BLOCK].index
gas['regime'].loc[indx]='post-merge'
#%%
#plots histograms
plt.hist(pre['gas_used'], density=True,alpha=0.7,label='EIP1559, pre-merge',bins=100)
plt.hist(merge['gas_used'], density=True,alpha=0.7,label='EIP1559, post-merge',bins=100)
plt.vlines(x=1.5e7,ymin=0,ymax=4.25e-7,label='Target block size',color='C2')
plt.xlabel('Gas used (gas units)')
plt.ylabel('Density')
plt.legend()
plt.title('Gas usage in the Ethereum network')
plt.ylim([0,1e-7])
plt.show()
#%%

#describes datasets
print('description, pre merge')
print(pre.describe())

print('description, post merge')
print(merge.describe())

#%%
#plots base fees

for aux,l in zip([pre,merge],['EIP1559, pre-merge','EIP1559, post-merge']):
    aux=aux['base_fee_per_gas']
    aux = aux[aux.between(aux.quantile(.01), aux.quantile(.99))] 
    plt.hist(np.log10(aux*10**-18), density=True,alpha=0.7,label=l,bins=100)

plt.xlabel('Log (Base Fee) (ETH per gas unit)')
plt.ylabel('Density')
plt.legend()
#plt.xscale('log')
plt.title(r'Log(Base fee) in the Ethereum network ($\log_{10}$-scale)')
plt.show()

#%%
props = dict(boxstyle='round')
#plots gas burn

names=['EIP1559, pre-merge','EIP1559, post-merge']
mus=[]
ss=[]
for aux,l in zip([pre,merge],names):
    aux['burn']=aux['base_fee_per_gas']*gas['gas_used']*10**-18
    aux=aux['burn']
    aux = aux[aux.between(aux.quantile(.01), aux.quantile(.99))] 
    plt.hist(aux, density=True,alpha=0.7,label=l,bins=100)
    plt.xlabel('Burnt tokens (ETH)')
    plt.ylabel('Density')
    plt.legend()
    plt.xlim([0,3])
    
    mus.append(round(aux.mean(),3))
    ss.append(round(aux.std(),3))
    
    

textstr = '\n'.join((
r'$\mu_{pre}=%.2f$' % (mus[0] ),
r'$\sigma_{pre}=%.2f$' % (ss[0] ),
r'$\mu_{post}=%.2f$' % (mus[1] ),
r'$\sigma_{post}=%.2f$' % (ss[1] ))
)        

plt.text(1., 3, textstr, fontsize=6,
verticalalignment='top', bbox=props)


plt.title(r'EIP1559 burning in the Ethereum network')
plt.show()

#%%
#plots time between blocks

for aux,l in zip([pre,merge],['EIP1559, pre-merge','EIP1559, post-merge']):
    plt.hist(aux['dt'], density=True,alpha=0.7,label=l,bins=100)
plt.xlabel('Time (s)')
plt.ylabel('Density')
plt.title(r'Time between blocks')
plt.ylim([0,0.1])
plt.xlim([0,70])
xx=np.linspace(0,70,100)
lam=1/(merge['dt'].dropna().mean())
plt.plot(xx, lam*np.exp(-lam *xx), label='Exp. Distr, $\lambda=$'+str(round(lam,2)))
plt.legend()
plt.xlim([0,50])
plt.xticks([0, 12, 24, 36, 48])
plt.show()
