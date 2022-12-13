import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .DataHandler import DataHandler

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

    def run(self, pool_address=None):
        df = self._dh.getData(pool_address=pool_address)
        df.block_timestamp = pd.to_datetime(df.block_timestamp)
        df.sort_values("block_timestamp", ascending=True, inplace=True)
        df["sqrtPrice"] = df["sqrtPrice"].apply(lambda x: int(x, 16))

        # let's deploy liquidity at a given time:
        # we identiy a position via it's time of deployment, width in percent, and amount:
        position = {"time": "2022-02-08 12:00:00", "width": 30, "amount": 1000}

        positionId = self.deployPosition(df, position)  # deploys a position

        fee = self._dh.getFee(pool_address=pool_address)

        # now collect fees up to some point
        fees = self.collectFees(df, positionId, till="2022-04-01 12:00:00", fee=fee)

        import pdb
        pdb.set_trace()
    
    def collectFees(self, df=None, positionId=None, till=None, fee=None):
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

        def _collect_fee(x, fee, feeMap):
            # process each row
            amount0 = self._twos_complement(x.amount0)
            amount1 = self._twos_complement(x.amount1)

            if amount0 < 0:
                feeCollected = -amount0
                theToken = "token0"
            else:
                feeCollected = -amount1
                theToken = "token1"
            feeCollected *= (fee / 10000) / 100

            # feeMap[token0] = ... # store collected fee under the map under each token
            # then, after this "apply" call we simply sum up both tokens (we just need to compare against the initial position)
            # perhaps we convert it all to USDC?
            # >>>> Or simply to token0 since we have the price of that...

            if theToken not in feeMap:
                feeMap[theToken] = 0
            
            feeMap[theToken] += feeCollected / 10 ** 18 # TODO: GENERALIZE THIS TO THE DECIMALS (USE DATAHANDLER!)

            # TODO: CONVERT ONE TOKEN TO THE OTHER USING THE PRICE AT SWAP!
            # TODO: PICK TOKEN0 AS THE UNIT!


        fee = chunk_inrange.apply(_collect_fee, args=(fee, feeMap), axis=1) # apply across rows

        # now feeMap has all fees

        
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

        deployedPosition = position.copy()
        deployedPosition["atPrice"] = price_after

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
