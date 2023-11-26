#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from computeQuantities import computeQuantities
from plotResults import plotComparisson

#%%
pools = ["0xa6Cc3C2531FdaA6Ae1A3CA84c2855806728693e8",
    "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed",
"0xa3f558aebaecaf0e11ca4b2199cc5ed341edfd74",
"0x290A6a7460B308ee3F19023D2D00dE604bcf5B42",
"0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"]

dfs=[]
names=[]


for pool_id in pools:
    
    df,name= computeQuantities(pool_id)
    dfs.append(df)
    names.append(name)
    
    print('plotting...')

    plotComparisson(df,name)
    print(f'done with {name}')
   
    
    '''
    Interesting alpha: Panoptions tends to prodcue a larger premia (than BSM) when:
        
        - relatively smaller r
        - relatively higher volatility (all but LDO-WETH)
        
        
        
        
    '''
    r_trunc=1.3

    print(f'Plotting, restricted to r={r_trunc}')
    
    # import pdb
    # pdb.set_trace()
    plotComparisson(df,name,truncation=r_trunc)
    print(f'done with {name}')
#%%    

    
