import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from DataHandler import DataHandler

class BackTester(object):
    """
    Backtest Panoptic strategies.
    """
    _start_date = None
    _end_date = None
    _dh = None
    Positions = None  #  track positions held; each position has a unique id
    
    def __init__(self):
        self._dh = DataHandler()
        self.Positions = dict()
        self.UNIV3_BASE=1.0001
    def run(self, pool_address:str=None,position:dict=None):
        # backtest should include an input strategy parameter
        df = self._dh.getData(pool_address=pool_address)
        df.block_timestamp = pd.to_datetime(df.block_timestamp)
        df.sort_values("block_timestamp", ascending=True, inplace=True)
        df["sqrtPrice"] = df["sqrtPrice"].apply(lambda x: int(x, 16))

        # let's deploy liquidity at a given time:
        # we identiy a position via it's time of deployment, width in percent, and amount:
        position = {"time": "2022-02-08 12:00:00", "width": 30, "amount": 1000, "pool":pool_address}
 
        
        positionId = self.deployPosition(df, position)  # deploys a position

        # now collect fees up to some point
        fees = self.collectFees(df, positionId, till="2022-04-01 12:00:00",fee=0.03)

        import pdb
        pdb.set_trace()
    
    def collectFees(self, df=None, positionId=None, till=None,fee:float=None):
        
        # TODO remove fee as a percentage  and make it readable directly from the pool address  
        
        strat0=[]
        strat1=[]
        strat2=[]
        
        
        till = pd.to_datetime(till, utc=True)
        end_index = df.block_timestamp.searchsorted(till)

        posDetails = self._getPosition(positionId)
        start_index = posDetails["atIndex"]

        chunk = df.iloc[start_index:end_index]
        chunk["price"] = self._sqrtPriceToPrice(chunk.sqrtPrice) 

        # TODO: REMOVE FIRST: let's plot the price evolution in the chunk!
        chunk.plot("block_timestamp", "price")
        plt.show()
        
        
        


        # TODO let's compute the fees within range
        # each line in the DF is a swap... if it happened within our tick range we collect fees (amount of pool fee on the input token!)...
        Nticks=len(chunk)
        ticks=list(df['tick'])
        
        
        tick_upper=posDetails['tick_upper']
        tick_lower=posDetails['tick_lower']
        atTick=posDetails['atTick']
        deltaL = self._getInitialLiq(atTick,tick_lower)
        dF0=0
        dF1=0
        nn=0
        
        startVal0 = self._getStart0(chunk.iloc[0].tick, tick_lower, tick_upper)
        startVal1 = 1
        
        for i in range(1,Nticks):
        

        
        
            if self._inRange(ticks,i,posDetails):

                dT = (ticks[i] - ticks[i-1])

                if dT > 0:
                    pLow = max(self._sqrtPriceToPrice(chunk.iloc[i-1].sqrtPrice), self.UNIV3_BASE**(tick_lower))
                    pHigh = min(self._sqrtPriceToPrice(chunk.iloc[i].sqrtPrice), self.UNIV3_BASE**(tick_upper))   
                    dy = deltaL*(pHigh - pLow)
                    dF1 += dy*fee
                elif dT < 0:
                    pLow = max(self._sqrtPriceToPrice(chunk.iloc[i].sqrtPrice), self.UNIV3_BASE**(tick_lower))
                    pHigh = min(self._sqrtPriceToPrice(chunk.iloc[i-1].sqrtPrice), self.UNIV3_BASE**(tick_upper))          
                    dx = deltaL*(1/pLow - 1/pHigh)        
                    dF0 += dx*fee
                nn += 1    
               
                endValue0 = self._getEnd0(ticks[i], tick_lower, tick_upper, deltaL)
                endValue1 = self._getEnd1(ticks[i], tick_lower, tick_upper, deltaL) 
        
                strat0.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue0*self.UNIV3_BASE**ticks[i] + endValue1 - 2) # Buy all
                strat1.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + (endValue0-startVal0)*self.UNIV3_BASE**ticks[i] + endValue1 - 1) # borrow token   
                strat2.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue1 + (endValue0-2*startVal0)*self.UNIV3_BASE**ticks[i]) # borrow all   
        
                strike = ticks[i]
                deltaL = self._getInitialLiq(atTick, tick_lower)
                startVal0 = self._getStart0(strike, tick_lower, tick_upper)
                startVal1 = 1
        
           
            self._updatePos(posDetails,df)


        import pdb
        pdb.set_trace()
    
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
        
        position['tick_lower']=tick+int(np.floor(self._loga(1-width/2,self.UNIV3_BASE)))
        position['tick_upper']=tick+int(np.ceil(self._loga(1+width/2,self.UNIV3_BASE)))
        
        
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
        




# startLiq = lambda t, tL : 1/(sqrt(1.0001**t)-sqrt(1.0001**tL))
# start0 = lambda t, tL, tH :  startLiq(t, tL)*(1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH))
# start1 = 1
# end0 = lambda t, tL, tH, dL : (t<= tL)*dL * (1/sqrt(1.0001**tL) - 1/sqrt(1.0001**tH)) + (t > tL)*(t<tH)*dL * (1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH)) + (t>=tH)*0
# end1 = lambda t, tL, tH, dL : (t<=tL)*0 + (t>tL)*(t<tH)*dL * (sqrt(1.0001**t) - sqrt(1.0001**tL))+(t>=tH)*dL * (sqrt(1.0001**tH) - sqrt(1.0001**tL))
# totalVal = start1 + start0(startTick, startTick - width, startTick + width)*1.0001**startTick

    
    def _updatePos(self,position,time):
        #TODO
        pass

    
if __name__=='__main__':
    bt=BackTester()
    POOL='0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c'
    position={"time": "2022-02-08 12:00:00", "width": 30, "amount": 1000}
    bt.run(pool_address=POOL)