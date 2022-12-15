#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is a working version of the collect fees code.
Created on Wed Dec 14 20:26:32 2022

@author: juan
"""
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pdb
import datetime


class feesTest:
    
    def __init__(self):
        self.UNIV3_BASE=1.0001
    

    def collectFees(self, df:pd.core.frame.DataFrame, positionId:dict, till:str=None,fee:float=0.3/100):
        
        # TODO remove fee as a percentage  and make it readable directly from the pool address  
        #positionId = self.deployPosition(df, positionId)  # deploys a position
        strat0=[]
        strat1=[]
        strat2=[]
        
        
        initialDate=positionId['time']
        chunk=self._getChunk(df,
                       initial=initialDate, 
                       end=None) # sorted wrt time

        
        ticks=list(chunk['tick'].values)
        strike=chunk['tick'][0]
        N=len(chunk)
   
        
        tick_upper=strike+1800#posDetails['tick_upper']
        tick_lower=strike-1800#posDetails['tick_lower']
        atTick=chunk['tick'][0]
        #atTick=posDetails['atTick']
        deltaL = self._getInitialLiq(atTick,tick_lower)
        dF0=0
        dF1=0
        nn=0
        
        
        
        
        startVal0 = self._getStart0(chunk.iloc[0].tick, tick_lower, tick_upper)
        startVal1 = 1#posDetails['amount']
        strike = chunk['tick'][0]
        width = 1800
        
        plt.subplot(2,1,1)
        plt.plot(chunk['block_timestamp'], ticks)

        print('💻🤓 computing fees...')
        start_time=df['block_timestamp'].iloc[0]
        for i in tqdm(range(1,N)):

            if ((ticks[i] < (strike + width)) and (ticks[i] > (strike - width))) or ((ticks[i-1] < (strike + width)) and (ticks[i-1] > (strike - width))) or (ticks[i-1] < (strike - width) and ticks[i] > (strike + width)) or (ticks[i-1] > (strike + width) and ticks[i] < (strike - width)):

        
                dT = (ticks[i] - ticks[i-1])
 

                if dT > 0:
                    pLow = max(chunk.iloc[i-1].sqrtPrice, self.UNIV3_BASE**(tick_lower/2))
                    pHigh = min(chunk.iloc[i].sqrtPrice, self.UNIV3_BASE**(tick_upper/2))   
                    dy = deltaL*(pHigh - pLow)
                    dF1 += dy*fee
                elif dT < 0:
                    pLow = max(chunk.iloc[i].sqrtPrice, self.UNIV3_BASE**(tick_lower/2))
                    pHigh = min(chunk.iloc[i-1].sqrtPrice, self.UNIV3_BASE**(tick_upper/2))          
                    dx = deltaL*(1/pLow - 1/pHigh)        
                    dF0 += dx*fee
            
            
            
            
            
            
            #This part of the code updates the strategies
            #This part of the code (i) collects the fees and (ii) updates the position every 1 day
            #TODO make the updating rule an input parameter
            if (df['block_timestamp'].iloc[i]-start_time) >datetime.timedelta(days=1):
            
            
            
                # obtained the end values
                endValue0 = self._getEnd0(ticks[i], tick_lower, tick_upper, deltaL)
                endValue1 = self._getEnd1(ticks[i], tick_lower, tick_upper, deltaL) 
        
                #updates each  strategy
                strat0.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue0*self.UNIV3_BASE**ticks[i] + endValue1 - 2) # Buy all
                strat1.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + (endValue0-startVal0)*self.UNIV3_BASE**ticks[i] + endValue1 - 1) # borrow token   
                strat2.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue1 + (endValue0-2*startVal0)*self.UNIV3_BASE**ticks[i]) # borrow all   
        
        
                #redeploys with a different width and whatnot
                strike = ticks[i]
                tick_upper=strike+width#posDetails['tick_upper']
                tick_lower=strike-width#posDetails['tick_lower']
                deltaL = self._getInitialLiq(strike, tick_lower)
                startVal0 = self._getStart0(strike, tick_lower, tick_upper)
                startVal1 = 1
                
                start_time=df['block_timestamp'].iloc[i]

            

            
                # import pdb
                # pdb.set_trace()
                dF0 = 0
                dF1 = 0   
                 
    
            
         #self._updatePos(posDetails,df)
        plt.subplot(2,1,2)

        plt.plot(np.cumsum(strat0[1:])-strat0[1], label="long")
        plt.plot(np.cumsum(strat1[1:])-strat1[1], label="neutral")
        plt.plot(np.cumsum(strat2[1:])-strat2[1], label='short')

        plt.plot([0, len(strat0)], [0,0], color='#231f20')
        plt.title('This is for the backtest!')
        plt.legend()   

        return [strat0,strat1,strat2]
    
    def deployPosition(self, df=None, position=None):
        atTime = pd.to_datetime(position["time"], utc=True)

        # for price, just get average of nearest prices:
        indexAfter = df.block_timestamp.searchsorted(atTime)
        indexBefore = max(0, indexAfter - 1)

        # get price deployed to
        # price_before = self._sqrtPriceToPrice(int(df.iloc[indexBefore].sqrtPrice, 16))
        price_after = self._sqrtPriceToPrice(df.iloc[indexAfter].sqrtPrice)
        # deployedAtPrice = np.average([price_before, price_after])
  
        # store details about our deployed range
        
        deployed_tick=df['tick'].iloc[indexAfter]
        
        # here we are assuming that width is given in percentages


        deployedPosition = position.copy()
        deployedPosition["atPrice"] = price_after
        deployedPosition["atBlock"] = int(df.iloc[indexAfter].block_number)
        deployedPosition["atTick"] = int(df.iloc[indexAfter].tick)  # this is when we assume the position was deployed with no impact to price
        deployedPosition["atIndex"] = indexAfter # the index in the pandas dataframe
        self._getTicksFromWidth(deployedPosition)

        # create position id
        positionId = self._getPositionId(position)
        self.Positions[positionId] = deployedPosition

        
        return positionId

    # =================================================================
    #                       Helpers
    # =================================================================
    def _sqrtPriceToPrice(self, sqrtPrice=None):
        return (sqrtPrice / 2 ** 96) ** 2
    
    def _getPositionId(self, position=None):
        return hashlib.sha256(str(tuple(position.values())).encode()).hexdigest()

    def _getPosition(self, positionId=None):
        return self.Positions[positionId]
    
    def _getTicksFromWidth(self,position):
        tick=position["atTick"] 
        width=position['width']/100
        
        
        #FORCING THIS FOR TEST

        
        position['tick_lower']=tick-1800#int(np.floor(self._loga(1-width/2,self.UNIV3_BASE)))
        position['tick_upper']=tick+1800#int(np.ceil(self._loga(1+width/2,self.UNIV3_BASE)))

        
    def _loga(self,x,a):
        return np.log(x)/np.log(a)
    
    def _inRange(self,ticks,i,position):
        ub=position['tick_upper']
        lb=position['tick_lower']
        
        isInRange= lb<ticks[i]<ub
        wasInRange=lb<ticks[i-1]<ub
        rangeCrossUp= ticks[i-1]<lb and ticks[i]>ub
        rangeCrossDown=ticks[i-1] > ub and ticks[i] < lb
        
        counts=isInRange or wasInRange or rangeCrossUp or rangeCrossDown
            
        return counts

    def _getInitialLiq(self,currentTick,lowerTick):
        return  1/(np.sqrt(self.UNIV3_BASE**currentTick)-np.sqrt(self.UNIV3_BASE**lowerTick))
        

    def _getStart0(self,currentTick,lowerTick,higherTick):
        L0=self._getInitialLiq(currentTick,lowerTick)
        return L0*(1/np.sqrt(self.UNIV3_BASE**currentTick) - 1/np.sqrt(self.UNIV3_BASE**higherTick))
    
    def _getEnd0(self,currentTick,lowerTick,higherTick,deltaL):
        a=(currentTick<= lowerTick)*deltaL * (1/np.sqrt(self.UNIV3_BASE**lowerTick) - 1/np.sqrt(self.UNIV3_BASE**higherTick))
        b= (currentTick > lowerTick)*(currentTick<higherTick)*deltaL * (1/np.sqrt(self.UNIV3_BASE**currentTick) - 1/np.sqrt(self.UNIV3_BASE**higherTick))
        c= (currentTick>=higherTick)*0
        
        return a+b+c

    def _getEnd1(self,currentTick,lowerTick,higherTick,deltaL):
        a=(currentTick<=lowerTick)*0
        b=(currentTick>lowerTick)*(currentTick<higherTick)*deltaL * (np.sqrt(self.UNIV3_BASE**currentTick) - np.sqrt(self.UNIV3_BASE**lowerTick))
        c=(currentTick>=higherTick)*deltaL * (np.sqrt(self.UNIV3_BASE**higherTick) - np.sqrt(self.UNIV3_BASE**lowerTick))
        
        return a+b+c
        
    def _getTotalVal(self,startTick,lowerTick,higherTick):      
        start1=1
        start1+self._getStart0(startTick,lowerTick,higherTick)*self.UNIV3_BASE**startTick
        
    
    
    def _updatePos(self,position,time):
        #TODO
        pass
    
    
    def _getChunk(self,df:pd.core.frame.DataFrame,
                   initial:str, 
                   end:str)->pd.core.frame.DataFrame:
        '''
        
        gets a chunk of data between initial and end
        Parameters
        ----------
        df : pd.core.frame.DataFrame
            dataframe we are dealing with
        initial : str
            initial data in Y-M-D H:mm:ss format
        end : str
            end data in Y-M-D H:mm:ss format

        Returns
        -------
        dff : pd.core.frame.DataFrame
            the chunk of data

        '''
        dff=df.sort_values(by='block_timestamp')
        if initial is not None:
            dff=df[df['block_timestamp']>=initial]
        if end is not None:
            dff=dff[dff['block_timestamp']<=end]
            
        dff['sqrtPrice']=dff['sqrtPrice'].apply(lambda x: int(x,16)/2**96)    
        
        return dff
        
        
#%%    
from tqdm import tqdm
tqdm.pandas()    
POOL='../strategyTest/aFewPools/0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c.csv'
#POOL='../strategyTest/0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801.csv'
df=pd.read_csv(POOL).progress_apply(lambda x: x)
df['block_timestamp']=pd.to_datetime(df['block_timestamp']).progress_apply(lambda x: x)
test=feesTest()
df=df.sort_values(by='block_timestamp')
start_date=df['block_timestamp'].iloc[0]
end_date=df['block_timestamp'].iloc[-1]

#%%
positionId={"time": start_date, "width": 1800, "amount": 1}
fees=test.collectFees(df,positionId=positionId,till=end_date,fee=0.3/100)

