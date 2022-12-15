import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .DataHandler import DataHandler
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
                    runmode:str,
                    position:dict,
                    untill:pd._libs.tslibs.timestamps.Timestamp=None):
        '''
        This is the run method. We use this to run a given strategy

        Parameters
        ----------
        pool_address : str
            the 0x... address of a pool. 
            TODO: allow this function to take the ticker of both coins 
            and the pool fee, e.g., ETH-USDC-0.3
        runmode : str
            one of {long, neutraal,short}
        position : dict
            TODO: I think this should become an object, with an update method
            A dictionary describing the initial position. 
            
            Position should have keys:
                token: str token0 or token1
                size: amount of token deployed
                ia: lowest tick to deploy
                ib: highest tick to deploy
        until: timestamp: 
            when to stop running the position. Default is None, in which case
            runs through the whole dataset
            


        Returns
        -------
        pd.core.frames.DataFrame witht the fees collected

        '''
        ######################################################
        #
        #
        #    1.   Initialises the dataset
        #
        #
        ######################################################
        
        self.runInfo["pool_address"] = pool_address
        df = self._dh.getData(pool_address=pool_address)
        
        
        
        
        

        initialDate=position['time']
        #converts df' block timestamp to d datetime object and then sorts it
        df.block_timestamp = pd.to_datetime(df.block_timestamp)
        df.sort_values("block_timestamp", ascending=True, inplace=True)
        #obtains a chunk of such a data
        chunk=self._getChunk(df,
                       initial=initialDate, 
                       end=untill) # sorted wrt time

        ######################################################
        #
        #
        #    2.   initialises values for the position
        #
        #
        ######################################################        
        #gets information from the position
        lowerTick=position['ia']
        higherTick=position['ib']          
        ticks=list(chunk['tick'].values)
        strike=chunk['tick'][0]
        N=len(chunk)
        
        

        
        plt.subplot(2,1,1)
        plt.plot(chunk['block_timestamp'], ticks)

        
                
        # TODO; 
        #
        # get fees
        # output this thing
        #
        # def _countFees(self,chunk:pd.core.frame.DataFrame
        #                ,position:dict,
        #                redeployFreq=datetime.timedelta(days=1),fee:float=0.3/100)
        
        
        
        # # assume the user deploys a position of this size (amount of token0):
        # if position['token']=='token0':
        # #following Guillaume's and this: 
        # #https://atiselsts.github.io/pdfs/uniswap-v3-liquidity-math.pdf
            
        
        


        # # how were the funds acquired? Borrowed? Etc.
        # if runmode == 0:
        # 	# the user provides all assets (token0 *and* token1)
        #     qtyToken0 = sizeTmp
        #     qtyToken1 = self._dh.tradeToken0(pool_address=pool_address, token0amount=qtyToken0)
            
        #     # there can be an approximation here what is the token0 equivalent amount (to be precise!)?
        #     qtyToken0 = self._dh.tradeToken1(pool_address=pool_address, token1amount=qtyToken1)

        #     # the user thus needs twice this - that is the size
        #     size = 2 * qtyToken0

        # # else if runmode == 1:
        # # 	# TODO the user borrows one of the tokens
        
        # # else if runmode == 2:
        # # 	# TODO the user borrows all of the tokens

        # self.runInfo["pool_address"] = pool_address

        # df = self._dh.getData(pool_address=pool_address)
        # df.block_timestamp = pd.to_datetime(df.block_timestamp)
        # df.sort_values("block_timestamp", ascending=True, inplace=True)
        # df["sqrtPrice"] = df["sqrtPrice"].apply(lambda x: int(x, 16))

        # # let's deploy liquidity at a given time:
        # # we identiy a position via it's time of deployment, width in percent, and amount:
        # position = {
        #     "time": "2022-02-08 12:00:00",
        #     "width": 30,
        #     "amountToken0": qtyToken0,
        #     "amountToken1": qtyToken1
        # }

        # positionId = self.deployPosition(df, position)  # deploys a position

        # # now collect fees up to some point
        # fees = self.collectFees(df, positionId, till="2022-04-01 12:00:00")

        # import pdb
        # pdb.set_trace()

    def collectFees(self, df=None, positionId=None, till=None):
        till = pd.to_datetime(till, utc=True)
        end_index = df.block_timestamp.searchsorted(till)

        posDetails = self._getPosition(positionId)
        start_index = posDetails["atIndex"]

        chunk = df.iloc[start_index:end_index]
        chunk["price"] = self._sqrtPriceToPrice(chunk.sqrtPrice)

        price_upper = self._tickToPrice(posDetails["higherTick"])
        price_lower = self._tickToPrice(posDetails["lowerTick"])
        
        # TODO: move to its own function (plotting fct)
        chunk.plot("block_timestamp", "price")
        plt.axhline(price_upper, linestyle="--", color="k")
        plt.axhline(price_lower, linestyle="--", color="k")
        plt.show()

        chunk_inrange = chunk[(chunk["price"] <= price_upper) & (chunk["price"] >= price_lower)]

        feeMap = dict()
        fee = self._dh.getFee(pool_address=self.runInfo["pool_address"])
        decimals = self._dh.getToken0(pool_address=self.runInfo["pool_address"]).decimals

        # apply function to collect fees
        def _collect_fee(x, fee, feeMap):
            # process each row
            amount0 = self._twos_complement(x.amount0)
            amount1 = self._twos_complement(x.amount1)

            if amount0 < 0:
                feeCollected = -amount0
            else:
                # Convert to amount0's
                # price is "how many token1s do we get per token0"
                # now we have the amount of token1s at hand - so we need to invert: "how many token0s do we get per token1":
                feeCollected = -amount1 / x.price

            # subtract fees paid to LPs
            feeCollected *= (fee / 10000) / 100

            # now take the amount owned by the user
            L = int(x.liquidity, 16)

            Lx = posDetails["amountToken0"]
            Ly = posDetails["amountToken1"]
            
            # the user's ownership:
            Lu = np.sqrt(float(Lx) * Ly)

            import pdb
            pdb.set_trace()

            # everything counted in token0
            if "token0" not in feeMap:
                feeMap["token0"] = 0
            
            feeMap["token0"] += feeCollected / 10 ** decimals

        # after this call, "feeMap" has all the fees
        chunk_inrange.apply(_collect_fee, args=(fee, feeMap), axis=1) # apply across rows
        fees = feeMap["token0"]  # how many token0s collected in fees


        import pdb
        pdb.set_trace()
    
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
        higherTick = int(np.floor(deployedPosition["atTick"] * (1 + (width / 2) / 100)))
        lowerTick = int(np.ceil(deployedPosition["atTick"] * (1 - (width / 2) / 100)))
        
        deployedPosition["lowerTick"] = lowerTick
        deployedPosition["higherTick"] = higherTick
        
        # actual width
        actual_width = (higherTick - lowerTick) / deployedPosition["atTick"] * 100
        deployedPosition["actual_width"] = actual_width

        # create position id
        positionId = self._getPositionId(position)
        self.Positions[positionId] = deployedPosition

        return positionId

    # def positionValue(self, atTick=None):

    #     ### TODO: WHAT IS THIS - GET VALUE OF A POSITION
    #     ### 
    #     startLiq = lambda t, tL : 1/(sqrt(1.0001**t)-sqrt(1.0001**tL)) # WHAT IS THIS EQ? WHY START LIQ?   1 / (sqrt(price) - sqrt(priceL))

        
    #     # So we just pick start1 (token1) to be 1? Then what is token0:
    #     start0 = lambda t, tL, tH :  startLiq(t, tL)*(1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH))
    #     start1 = 1

    #     # this is just the conditional on token0 saying:
    #     # the value to it comes from 3 cases: "t <= tL": ...
    #     # t is in between, and t > tH --- SEE the uniswap options book from Peter
    #     # this simply gives the value of token0 at some tick t
    #     # same with token1 - check as well
        
    #     end0 = lambda t, tL, tH, dL : (t<= tL)*dL * (1/sqrt(1.0001**tL) - 1/sqrt(1.0001**tH)) + (t > tL)*(t<tH)*dL * (1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH)) + (t>=tH)*0
    #     end1 = lambda t, tL, tH, dL : (t<=tL)*0 + (t>tL)*(t<tH)*dL * (sqrt(1.0001**t) - sqrt(1.0001**tL))+(t>=tH)*dL * (sqrt(1.0001**tH) - sqrt(1.0001**tL))

    #     # total val then takes the start liquidities and adds them
    #     totalVal = start1 + start0(startTick, startTick - width, startTick + width)*1.0001**startTick

    #     # here is the liquidity at strike - width:
    #     deltaL = startLiq(startTick, strike - width)

    #     startVal0 = start0(startTick, strike -width, strike+width)
    #     startVal1 = 1
        


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
                       higherTick:int,amount:float):
        
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
        
    
        if Range=='Below':
            Token1=0
            Token0=amount
            L=Token0*(pa*pb)**0.5/(pb**0.5-pa**0.5)
        
        if Range=='Above':
            Token0=0
            Token1=amount
            L=amount/(pb**0.5-pa**0.5)
            
            
            
            
        if Range=='Inside':
            
            if whichToken=='Token1':
                L=amount/(P**0.5-pa**0.5)
                Token1=amount
                Token0=L*(pb**0.5-P**0.5)/((P*pb)**0.5)
                
            else:
                L=amount*(P*pb)**0.5/(pb**0.5-P**0.5)
                Token0=amount
                Token1=L*(P**0.5-pa**0.5)
     
                
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
        
        
        currentTick=chunk['tick'].iloc[0]
        lowerTick=position['ia']
        higherTick=position['ib']
        amount=position['amount']
        whichToken=position['Token']
        width=position['Width']
        deltaL,startVal0,startVal1=self._getLiquidityAndTokens(whichToken=whichToken,
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
        for i in tqdm(range(1,N)):
            if self.inRange(ticks,i,lowerTick,higherTick):

        
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
                deltaL,endValue0,endValue1=self._getLiquidityAndTokens(whichToken=whichToken,
                                   currentTick=ticks[i],
                                   lowerTick=lowerTick,
                                   higherTick=higherTick,amount=amount)            
            

        
                #updates each  strategy
                strat0.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue0*self.UNIV3_BASE**ticks[i] + endValue1 - 2*amount) # Buy all
                strat1.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + (endValue0-startVal0)*self.UNIV3_BASE**ticks[i] + endValue1 - 1*amount) # borrow token0   
                strat2.append(dF0*self.UNIV3_BASE**ticks[i] + dF1 + endValue1 + (endValue0-2*startVal0)*self.UNIV3_BASE**ticks[i]) # borrow all   

                #redeploys with a different width and whatnot
                
                strike = ticks[i]
                higherTick=strike+width
                lowerTick=strike-width
                #closes position and obtains the end values
                deltaL,startVal0,startVal1=self._getLiquidityAndTokens(whichToken=whichToken,
                                   currentTick=ticks[i],
                                   lowerTick=lowerTick,
                                   higherTick=higherTick,amount=amount)            
            

                
                start_time=chunk['block_timestamp'].iloc[i]


                dF0 = 0
                dF1 = 0   


