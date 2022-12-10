"""
DataHandler for storing and loading pool data.
@author: Jesper Kristensen, Panoptic.xyz
"""
from pathlib import Path
import pandas as pd


"""DataHandler"""
class DataHandler(object):
    _filePath = None  # where is data stored
    _path = None

    def __init__(self, file=".data/data.csv"):
        self._filePath = Path(file)
        self._filePath.parents[0].mkdir(parents=True, exist_ok=True)
        self._path = str(self._filePath.absolute())

    """Download data from Google BigQuery Table"""
    def download(self, pool_address=None, all=False, force=False):
        assert(pool_address is not None)

        if self._filePath.exists() and not force:
            print("🐇 Data already exists! Call with `force=True` to re-download! Returning cached data.")
            return pd.read_csv(self.path())
        
        df = pd.read_gbq(f"SELECT * FROM `arcane-world-371019.First_sync.1` WHERE address='{pool_address}' {'' if all else 'LIMIT 1000'}", project_id="arcane-world-371019", progress_bar_type='tqdm')
        df.to_csv(self.path(), index=False)
        return df

    """View functions"""
    def getData(self):
        return pd.read_csv(self.path())

    def path(self):
        return self._path
