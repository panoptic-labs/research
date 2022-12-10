"""
DataHandler for storing and loading pool data.
@author: Jesper Kristensen, Panoptic.xyz
"""
import datetime
import os
from pathlib import Path
import pandas as pd
from uniswap import Uniswap
from uniswap.token import ERC20Token
from web3 import Web3, HTTPProvider
from dotenv import load_dotenv
load_dotenv() # loads your .env file - see ".env.example"

NUM_DAYS_TO_TRIGGER_WARNING = 7

"""DataHandler"""
class DataHandler(object):
    _filePath = None  # where is data stored
    _path = None
    _provider_url = None
    # _uniswap = None
    _w3 = None
    _latest_block_public = None
    _latest_timestamp_public = None
    _latest_block_local = None

    def __init__(self, datafolder=".data/"):
        self._filePath = Path(datafolder)
        self._filePath.mkdir(parents=True, exist_ok=True)
        self._path = str(self._filePath.absolute())

        self._provider_url = f"https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}"

        self._w3 = Web3(HTTPProvider(self._provider_url))
        assert(self._w3.isConnected())
        self._latest_block_public = self._w3.eth.block_number
        self._latest_timestamp_public = datetime.datetime.fromtimestamp(self._w3.eth.getBlock(self._w3.eth.block_number).timestamp)
        print(f"🔗 Latest block on the public blockchain: {self._latest_block_public} (public chain most recent timestamp: {self._latest_timestamp_public})")

        # self._uniswap = Uniswap(address=None, private_key=None, version=3, provider=f"https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}")
        
    """Download data from Google BigQuery Table"""
    def download(self, pool_address=None, all=False, force=False):
        assert(pool_address is not None)

        filepath = (self._filePath / pool_address).with_suffix(".csv")

        if filepath.exists() and not force:
            print("🐇 Local data found on disk! Returning cached data. Call with `force=True` to re-download all data to disk again!")

            self._latest_block_local = int(pd.read_csv(filepath).max().block_number)
            
            local_sync_time = datetime.datetime.fromtimestamp(self._w3.eth.getBlock(self._latest_block_local).timestamp)
            print(f"💻 Latest block on your local computer: {self._latest_block_local} (local most recent timestamp: {local_sync_time})")
        
            if (self._latest_timestamp_public - local_sync_time).total_seconds() > 3600 * 24 * NUM_DAYS_TO_TRIGGER_WARNING:
                print("⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠")
                print(f"                                                                                     ")
                print(f"    You are out of sync by more than {NUM_DAYS_TO_TRIGGER_WARNING} days!             ")
                print(f"                    >>> Forcing a re-download! <<<                                   ")
                print(f"                                                                                     ")
                print("⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠")
                
                return self.download(pool_address=pool_address, all=True, force=True)

            return pd.read_csv(filepath)
        
        df = pd.read_gbq(f"SELECT * FROM `arcane-world-371019.First_sync.1` WHERE address='{pool_address}' {'' if all else 'LIMIT 1000'}", project_id="arcane-world-371019", progress_bar_type='tqdm')
        df.to_csv(filepath, index=False)
        print(f"✍ Data written to: {filepath}")
        return df

    """View functions"""
    def getData(self):
        return pd.read_csv(self.path())

    def path(self):
        return self._path
