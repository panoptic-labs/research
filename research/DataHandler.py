"""
DataHandler for storing and loading pool data.
@author: Jesper Kristensen, Axicon Labs Inc.
"""
import datetime
import json
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
    _poolContracts = None # map pool address to pool contract
    _tokenContracts = None # map token address to token contract

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

        self._uniswap = Uniswap(address=None, private_key=None, version=3, provider=f"https://eth-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY')}")
        
    """Download data from Google BigQuery Table"""
    def download(self, pool_address=None, all=False, force=False):
        assert(pool_address is not None)

        filepath = self._getFilepath(pool_address=pool_address)

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
    def _getFilepath(self, pool_address=None):
        return (self._filePath / pool_address).with_suffix(".csv")

    def getData(self, pool_address=None):
        filepath = self._getFilepath(pool_address)
        if not filepath.exists():
            self.download(pool_address=pool_address, all=True)
        
        return pd.read_csv(filepath)

    def path(self):
        return self._path

    def getUniswapPoolAddress(self, token0address=None, token1address=None, fee=None):
        return self._uniswap.get_pool_instance(token0address, token1address, fee)

    """
    Returns
    poolContract.factory(),
    poolContract.token0(),
    poolContract.token1(),
    poolContract.fee(),
    poolContract.tickSpacing(),
    poolContract.maxLiquidityPerTick(),
    """
    def getPoolInfo(self, pool_address=None):
        # create pool contract
        poolContract = self._getPoolContract(pool_address)
        return self._uniswap.get_pool_immutables(poolContract)
    
    def getPoolContract(self, pool_address=None):
        return self._getPoolContract(pool_address=pool_address)
    
    def getToken0(self, pool_address=None):
        tokenAddress = self.getPoolInfo(pool_address=pool_address)["token0"]
        return self._uniswap.get_token(tokenAddress)
    
    def getToken1(self, pool_address=None):
        tokenAddress = self.getPoolInfo(pool_address=pool_address)["token1"]
        return self._uniswap.get_token(tokenAddress)
    
    def _checkSum(self, pool_address=None):
        return Web3.toChecksumAddress(pool_address)

    def _getTokenContract(self, token_address=None):
        # cache the token contract:
        if self._tokenContracts is not None and token_address in self._tokenContracts and self._tokenContracts[token_address] is not None:
            return self._tokenContracts[token_address]
        
        # load the abi:
        with open("research/aux/uniswapTokenABI.json", "r") as f:
            abi = json.load(f)["abi"]
        
        tokenContract = self._w3.eth.contract(
            address=self._checkSum(token_address),
            abi=abi
        )
        if self._tokenContracts is None:
            self._tokenContracts = dict()
        
        self._tokenContracts[token_address] = tokenContract

        return tokenContract

    def _getPoolContract(self, pool_address=None):
        # cache the pool contract:
        if self._poolContracts is not None and pool_address in self._poolContracts and self._poolContracts[pool_address] is not None:
            return self._poolContracts[pool_address]
        
        # load the abi:
        with open("research/aux/uniswapPoolABI.json", "r") as f:
            abi = json.load(f)["abi"]
        
        poolContract = self._w3.eth.contract(
            address=self._checkSum(pool_address),
            abi=abi
        )
        if self._poolContracts is None:
            self._poolContracts = dict()
        
        self._poolContracts[pool_address] = poolContract

        return poolContract
