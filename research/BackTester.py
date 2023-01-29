import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .DataHandler import DataHandler

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
    
    @withRunResetting
    def run(self, pool_address=None, runmode=0):
        # assume the user deploys a position of this size (amount of token0):
        sizeTmp = 1000
        size = None # the actual position size of the user

        # how were the funds acquired? Borrowed? Etc.
        if runmode == 0:
        	# the user provides all assets (token0 *and* token1)
            qtyToken0 = sizeTmp
            qtyToken1 = self._dh.tradeToken0(pool_address=pool_address, token0amount=qtyToken0)
            
            # there can be an approximation here what is the token0 equivalent amount (to be precise!)?
            qtyToken0 = self._dh.tradeToken1(pool_address=pool_address, token1amount=qtyToken1)

            # the user thus needs twice this - that is the size
            size = 2 * qtyToken0

        # else if runmode == 1:
        # 	# TODO the user borrows one of the tokens
        
        # else if runmode == 2:
        # 	# TODO the user borrows all of the tokens

        self.runInfo["pool_address"] = pool_address

        df = self._dh.getData(pool_address=pool_address)
        df.block_timestamp = pd.to_datetime(df.block_timestamp)
        df.sort_values("block_timestamp", ascending=True, inplace=True)
        df["sqrtPrice"] = df["sqrtPrice"].apply(lambda x: int(x, 16))

        # let's deploy liquidity at a given time:
        # we identiy a position via it's time of deployment, width in percent, and amount:
        position = {
            "time": "2022-02-08 12:00:00",
            "width": 30,
            "amountToken0": qtyToken0,
            "amountToken1": qtyToken1
        }

        positionId = self.deployPosition(df, position)  # deploys a position

        # now collect fees up to some point
        fees = self.collectFees(df, positionId, till="2022-04-01 12:00:00")

        import pdb
        pdb.set_trace()

    def collectFees(self, df=None, positionId=None, till=None):
        till = pd.to_datetime(till, utc=True)
        end_index = df.block_timestamp.searchsorted(till)

        posDetails = self._getPosition(positionId)
        start_index = posDetails["atIndex"]

        chunk = df.iloc[start_index:end_index]
        chunk["price"] = self._sqrtPriceToPrice(chunk.sqrtPrice)

        price_upper = self._tickToPrice(posDetails["tick_upper"])
        price_lower = self._tickToPrice(posDetails["tick_lower"])
        
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

    def positionValue(self, atTick=None):

        ### 
        startLiq = lambda t, tL : 1/(sqrt(1.0001**t)-sqrt(1.0001**tL))
        
        # So we just pick start1 (token1) to be 1? Then what is token0:
        start0 = lambda t, tL, tH :  startLiq(t, tL)*(1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH))
        start1 = 1

        end0 = lambda t, tL, tH, dL : (t<= tL)*dL * (1/sqrt(1.0001**tL) - 1/sqrt(1.0001**tH)) + (t > tL)*(t<tH)*dL * (1/sqrt(1.0001**t) - 1/sqrt(1.0001**tH)) + (t>=tH)*0
        end1 = lambda t, tL, tH, dL : (t<=tL)*0 + (t>tL)*(t<tH)*dL * (sqrt(1.0001**t) - sqrt(1.0001**tL))+(t>=tH)*dL * (sqrt(1.0001**tH) - sqrt(1.0001**tL))

        # total val then takes the start liquidities and adds them
        totalVal = start1 + start0(startTick, startTick - width, startTick + width)*1.0001**startTick

        # here is the liquidity at strike - width:
        deltaL = startLiq(startTick, strike - width)

        startVal0 = start0(startTick, strike -width, strike+width)
        startVal1 = 1
        


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
