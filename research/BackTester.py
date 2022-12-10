from .DataHandler import DataHandler

class BackTester(object):
    """
    Backtest Panoptic strategies.
    """
    _start_date = None
    _end_date = None
    _dh = None

    def __init__(self):
        self._dh = DataHandler()

    def run(self, pool_address=None):
        df = self._dh.getData(pool_address=pool_address)

        # now do with the data as you like...
        # TODO: add more helpers to the datahandler to get data more easily such as "max historical price", and so on... we can see based on usage
