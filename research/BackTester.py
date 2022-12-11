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

        # TODO: REMOVE FIRST: let's plot the price evolution in the chunk!
        chunk.plot("block_timestamp", "price")
        plt.show()

        # TODO let's compute the fees within range
        # each line in the DF is a swap... if it happened within our tick range we collect fees (amount of pool fee on the input token!)...

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
        tick_lower = # TODO...
        tick_upper = # TODO...

        deployedPosition = position.copy()
        deployedPosition["atPrice"] = price_after
        deployedPosition["atBlock"] = int(df.iloc[indexAfter].block_number)
        deployedPosition["atTick"] = int(df.iloc[indexAfter].tick)  # this is when we assume the position was deployed with no impact to price
        deployedPosition["atIndex"] = indexAfter # the index in the pandas dataframe

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