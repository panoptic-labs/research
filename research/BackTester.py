import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#uncomment!
#from .DataHandler import DataHandler
from DataHandler import DataHandler

import datetime
from tqdm import tqdm
# Decorator to reset a run
def withRunResetting(func):
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        # reset the runInfo dict:
        args[0].runInfo = dict()
    return wrapper


class BackTester(object):
    """
    Backtest Panoptic strategies.
    """
    _start_date = None
    _end_date = None
    _dh = None
    Positions = None  #  track positions held; each position has a unique id
    runInfo = None # things we need to pass around during a single run
    
    def __init__(self):
        self._dh = DataHandler()
        self.Positions = dict()
        self.runInfo = dict()
        self.UNIV3_BASE=1.0001
    @withRunResetting
    def run(self, pool_address:str,
            position:dict,
            fee:float=0.3/100,end_date=None):
        

        
        
        # adds relevant info for df
        df = self._dh.getData(pool_address=pool_address)
        df.block_timestamp = pd.to_datetime(df.block_timestamp)
        df.sort_values("block_timestamp", ascending=True, inplace=True)        
        if position['time'] is None:
            position['time']=df['block_timestamp'].iloc[0]
        # sorts and returns the chunk. it also adds the sqrtPrice
        chunk=self._getChunk(df, initial=position['time'], end=end_date)
        
        
        # gets relevant position stuff
        position['currentTick']=chunk['tick'].iloc[0]
        position['ib']=position['currentTick']+position['width']
        position['ia']=position['currentTick']-position['width']
        

        results=self._countFees(chunk=chunk,
                       position=position,
                       redeployFreq=datetime.timedelta(days=1),fee=fee)

        return results

    
    def deployPosition(self, df=None, position=None):
        atTime = pd.to_datetime(position["time"], utc=True)

        # get amount of token1 we need:
        amnt0 = position["amountToken0"]

        # for price, just get average of nearest prices:
        indexAfter = df.block_timestamp.searchsorted(atTime)
        # indexBefore = max(0, indexAfter - 1)

        # get price deployed to
        # price_before = self._sqrtPriceToPrice(int(df.iloc[indexBefore].sqrtPrice, 16))
        price_after = self._sqrtPriceToPrice(df.iloc[indexAfter].sqrtPrice)
        # deployedAtPrice = np.average([price_before, price_after])

        deployedPosition = position.copy()
        deployedPosition["atPrice"] = price_after
        deployedPosition["amountToken0"] = position["amountToken0"]
        deployedPosition["amountToken1"] = position["amountToken1"]

        # store details about our deployed range
        deployedPosition["atBlock"] = int(df.iloc[indexAfter].block_number)
        deployedPosition["atTick"] = int(df.iloc[indexAfter].tick)  # this is when we assume the position was deployed with no impact to price
        deployedPosition["atIndex"] = indexAfter # the index in the pandas dataframe

        width = position["width"] # percent
        tick_upper = int(np.floor(deployedPosition["atTick"] * (1 + (width / 2) / 100)))
        tick_lower = int(np.ceil(deployedPosition["atTick"] * (1 - (width / 2) / 100)))
        
        deployedPosition["tick_lower"] = tick_lower
        deployedPosition["tick_upper"] = tick_upper
        
        # actual width
        actual_width = (tick_upper - tick_lower) / deployedPosition["atTick"] * 100
        deployedPosition["actual_width"] = actual_width

        # create position id
        positionId = self._getPositionId(position)
        self.Positions[positionId] = deployedPosition

        return positionId

    

    # =================================================================
    #                       Helpers
    # =================================================================
    def _sqrtPriceToPrice(self, sqrtPrice=None):
        # because sqrtPrice is to 96 precision (sqrtPriceX96), we divide out by 2 ** 96
        return (sqrtPrice / 2 ** 96) ** 2
    
    def _tickToPrice(self, tick=None):
        return 1.0001 ** tick
    
    def _getPositionId(self, position=None):
        return hashlib.sha256(str(tuple(position.values())).encode()).hexdigest()

    def _getPosition(self, positionId=None):
        return self.Positions[positionId]
    
    def _twos_complement(self, hexstr=None):
        bits = 32 * 8 # all strings are 32 bytes
        value = int(hexstr,16)
        if value & (1 << (bits - 1)):
            value -= 1 << bits
        return value
    
    # =================================================================
    #                       Helpers
    # =================================================================
    def _sqrtPriceToPrice(self, sqrtPrice=None):
        return (sqrtPrice / 2 ** 96) ** 2
    
    def _getPositionId(self, position=None):
        return hashlib.sha256(str(tuple(position.values())).encode()).hexdigest()
 
    def _getPosition(self, positionId=None):
        return self.Positions[positionId]
    
        
    def _loga(self,x,a):
        return np.log(x)/np.log(a)
    
 
 
    def _getLiquidityAndTokens(self,whichToken:str,
                       currentTick:int,
                       lowerTick:int,
                       higherTick:int,amount:float,
                       deltaL:float=None,
                       end:bool=False):
        
        #TODO pass position object (once done) instead of ticsk and amount
        # this is a generalization of the starting liquidity, stari and endi
        #codes in G's notebook
        '''
        
        Returns the amount of tokens and the liquidity for a given position,
        given an amount of one of the tokens, a price, and the position width
        
        Reference:
        https://atiselsts.github.io/pdfs/uniswap-v3-liquidity-math.pdf
        https://lambert-guillaume.medium.com/understanding-the-value-of-uniswap-v3-liquidity-positions-cdaaee127fe7
    
        Parameters
        ----------
        whichToken : str
            Either Token0 or Token1. Describes which quantity we have.
        currentTick : int
            tick of the current price (in tick space)
        lowerTick : int
            tick of the lower end of position (in tick space)
        higherTick : int
            tick of high end of position (in tick space)
        amount : float
            Amount of either token 1 or token 0 to deploy.
        deltaL : float
            Liquidity, if needs to be forced
    
        Returns
        -------
        L : float
            liquidity of position.
        Token0 : float
            amount of token0 in this position.
        Token1 : float
            amount of token1 in this position.
    
        '''
                
        
        base=self.UNIV3_BASE
        
        ia=lowerTick
        ib=higherTick
        
        pa=base**ia
        pb=base**ib
        P=base**currentTick        
        
        #checks if in range
        if ia<=currentTick<=ib:
            Range='Inside'
        elif currentTick<ia:
            Range='Below'
        else:
            Range='Above'
        
        L=deltaL
        if Range=='Below':
            Token1=0
            Token0=amount
            if deltaL is None:
                L=Token0*(pa*pb)**0.5/(pb**0.5-pa**0.5)
        
        if Range=='Above':
            Token0=0
            Token1=amount
            if deltaL is None:
                L=amount/(pb**0.5-pa**0.5)
            
            
            
            
        if Range=='Inside':
            
            if whichToken=='Token1':
                if deltaL is None:
                    L=amount/(P**0.5-pa**0.5)
     
                Token1=amount
                if end:
                    Token1=L*(P**0.5-pa**0.5)
                Token0=L*(pb**0.5-P**0.5)/((P*pb)**0.5)
                
            else:
                if deltaL is None:
                    L=amount*(P*pb)**0.5/(pb**0.5-P**0.5)
                Token0=amount
                if end:
                    Token0=L*(pb**0.5-P**0.5)/((P*pb)**0.5)

                Token1=L*(P**0.5-pa**0.5)
                
                          

        

        # import pdb
        # pdb.set_trace()
                
        return L,Token0,Token1
            
    
        
 
    
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
 
 
    def _inRange(self,ticks,i,lowerTick,higherTick):
        
        
        
        
        ''' checks if we want to include a tick'''
        if ((ticks[i] < (higherTick)) and (ticks[i] > (lowerTick))) or ((ticks[i-1] < (higherTick)) and (ticks[i-1] > (lowerTick))) or (ticks[i-1] < (lowerTick) and ticks[i] > (higherTick)) or (ticks[i-1] > (higherTick) and ticks[i] < (lowerTick)):
            return True
        else:
            return False
    
 
    def _countFees(self,chunk:pd.core.frame.DataFrame
                   ,position:dict,
                   redeployFreq=datetime.timedelta(days=1),fee:float=0.3/100):
        
        
        
        print(' getting initial values...')

        
        currentTick=chunk['tick'].iloc[0]
        lowerTick=position['ia']
        higherTick=position['ib']
        amount=position['amount']
        whichToken=position['Token']
        width=position['width']
        deltaL,startValue0,startValue1=self._getLiquidityAndTokens(whichToken=whichToken,
                           currentTick=currentTick,
                           lowerTick=lowerTick,
                           higherTick=higherTick,amount=amount)
        
        
        ticks=list(chunk['tick'])
        N=len(ticks)
        
        # fees collected from either token
        dF1=0
        dF0=0 
        
        strat0=[]
        strat1=[]
        strat2=[]
        start_time=chunk['block_timestamp'].iloc[0]
        
        print('initial values')
        print([deltaL,startValue0,startValue1])
        
        
        strike=ticks[0]
        # import pdb
        
        # pdb.set_trace()
        
        print(' 🤓  counting fees...')
        
        for i in tqdm(range(1,N)):
            if ((ticks[i] < (strike + width)) and (ticks[i] > (strike - width))) or ((ticks[i-1] < (strike + width)) and (ticks[i-1] > (strike - width))) or (ticks[i-1] < (strike - width) and ticks[i] > (strike + width)) or (ticks[i-1] > (strike + width) and ticks[i] < (strike - width)):
 
        
                dT = (ticks[i] - ticks[i-1])
 
 
                if dT > 0:
                    pLow = max(chunk.iloc[i-1].sqrtPrice, self.UNIV3_BASE**(lowerTick/2))
                    pHigh = min(chunk.iloc[i].sqrtPrice, self.UNIV3_BASE**(higherTick/2))   
                    dy = deltaL*(pHigh - pLow)
                    dF1 += dy*fee
                elif dT < 0:
                    pLow = max(chunk.iloc[i].sqrtPrice, self.UNIV3_BASE**(lowerTick/2))
                    pHigh = min(chunk.iloc[i-1].sqrtPrice, self.UNIV3_BASE**(higherTick/2))          
                    dx = deltaL*(1/pLow - 1/pHigh)        
                    dF0 += dx*fee
            
            
            
 
 
 
            #This part of the code updates the strategies
            #This part of the code (i) collects the fees and (ii) updates the position every 1 day
            #TODO make the updating rule an input parameter
            ################################################################################################
            #
            #       This chunk updates the position every redeployFreq time
            #
            ###############################################################################################
            
            
            
            if (chunk['block_timestamp'].iloc[i]-start_time) >redeployFreq:
            
                #closes position and obtains the end values
                _,endValue0,endValue1=self._getLiquidityAndTokens(whichToken=whichToken,
                                   currentTick=ticks[i],
                                   lowerTick=lowerTick,
                                   higherTick=higherTick,amount=amount,
                                   deltaL=deltaL, end=True)            
            
 
    
    
   
                #updates each  strategy
                strat0.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue0*self.UNIV3_BASE**ticks[i] + endValue1 - 2*amount) # Buy all
                strat1.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + (endValue0-startValue0)*self.UNIV3_BASE**ticks[i] + endValue1 - 1*amount) # borrow token   
                strat2.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue1 + (endValue0-2*startValue0)*self.UNIV3_BASE**ticks[i]) # borrow all   
        
        
                #redeploys with a different width and whatnot
                
                strike = ticks[i]
                higherTick=strike+width
                lowerTick=strike-width
                
                # import pdb
                # pdb.set_trace()
                
                #closes position and obtains the end values
                deltaL,startValue0,startValue1=self._getLiquidityAndTokens(whichToken=whichToken,
                                   currentTick=ticks[i],
                                   lowerTick=lowerTick,
                                   higherTick=higherTick,
                                   amount=amount)
                
                
                #print('redeployed!')
            
                #print(deltaL,startValue0,startValue1)
 
                
                start_time=chunk['block_timestamp'].iloc[i]

                #print([deltaL,startValue0,startValue1])
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

        # return [strat0,strat1,strat2]
        # import pdb
        #pdb.set_trace()



    
    
bt = BackTester()

POS={'Token':'Token1',
          'amount':1,
          'width':1800,
          'time':None}
POOL= "0x1d42064fc4beb5f8aaf85f4617ae8b3b5b8bd801"

bt.run(pool_address=POOL,
       position=POS
       )   
    
    
    
    
    
    
    