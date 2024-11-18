import requests
import pandas as pd
import time
from tqdm import tqdm
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import ccxt

def date_to_timestamp(date_str):
    """
    Convert date string (YYYY-MM-DD) to UNIX timestamp in milliseconds.
    """
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return int(dt.timestamp() * 1000)


def timestamp_to_date_string(timestamp):
    """
    Convert UNIX timestamp (in milliseconds) to human-readable date string.
    """
    return datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

def get_next_day(date_string):
    try:
        # Try to parse the full datetime string
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # If parsing the full datetime fails, parse just the date string
        date_obj = datetime.strptime(date_string, "%Y-%m-%d")
    
    # Add one day to the parsed date
    next_day = date_obj + timedelta(days=1)
    
    # Return the next day as a string, keeping the original format
    if " " in date_string:
        return next_day.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return next_day.strftime("%Y-%m-%d")


    # Let's create a class for Deribit Options Trades data:

class Deribit_Options:
    def __init__(self, currency,start, end):
        self.start = start
        self.end = end 
        self.currency = currency
        self.base_url = "https://www.deribit.com/api/v2/public/"
        self.instruments = self.get_instruments()
    
    def get_instruments(self):
        """
        Fetches available option instruments for the selecgted currency.
        """
        url = f"{self.base_url}get_instruments?currency={self.currency}&kind=option"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error fetching instruments: {response.status_code}")
        instruments = response.json().get('result', [])
        return instruments

    def get_instrument_names(self):
        """
        Extracts the instrument names from the fetched instruments.
        """
        return [instrument['instrument_name'] for instrument in self.instruments]

    def get_trades_by_ticker(self, instrument_name, start_timestamp, end_timestamp):
        """
        Fetch ETH option trades by a specific ticker (instrument name) and retrieve Greeks.
        """
        url = f"{self.base_url}get_last_trades_by_instrument_and_time"
        params = {
            "instrument_name": instrument_name,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "count": 100
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Error fetching trades: {response.status_code} - {response.json()}")
        
        trades = response.json().get('result', {}).get('trades', [])

        # Fetch Greeks for each trade
        for trade in trades:
            greeks = self.get_greeks_by_instrument(instrument_name)
            trade.update(greeks)  # Add the Greeks to the trade details

        return trades

    def get_greeks_by_instrument(self, instrument_name):
        """
        Fetch the Greeks (Delta, Gamma, Vega, Theta, Rho) for a specific instrument hehe
        """
        url = f"{self.base_url}ticker?instrument_name={instrument_name}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error fetching Greeks: {response.status_code} - {response.json()}")
        
        greeks = response.json().get('result', {}).get('greeks', {})
        return greeks

    
    def get_instrument_details(self, instrument_name):
        """
        Fetch the details of a specific instrument (strike price, expiry, type)
        """
        for instrument in self.instruments:
            if instrument['instrument_name'] == instrument_name:
                return {
                    "strike": instrument['strike'],
                    "expiry": self.timestamp_to_date_string(instrument['expiration_timestamp']),
                    "option_type": instrument['option_type']
                }
        return None
    
    def fetch_current_index_price(self):
        """
        Fetch the current index price for the underlying currency (for calculating moneyness).
        """
        url = f"{self.base_url}ticker?instrument_name={self.currency}-PERPETUAL"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Error fetching index price: {response.status_code}")
            
        return response.json().get('result', {}).get('index_price')

    def calculate_moneyness(self, strike_price, index_price, option_type):
        """
        Calculate moneyness for an option (ITM, OTM, ATM)
        """
        if option_type == "call":
            if index_price > strike_price:
                return "ITM"  # In the money
            elif index_price < strike_price:
                return "OTM"  # Out of the money
            else:
                return "ATM"  # At the money
        elif option_type == "put":
            if index_price < strike_price:
                return "ITM"
            elif index_price > strike_price:
                return "OTM"
            else:
                return "ATM"
    
    def fetch_option_trades_to_df(self, tickers, start_date, end_date):
        """
        Fetch all trades for selected ETH options tickers and convert to DataFrame.
        """
        start_timestamp = self.date_to_timestamp(start_date)
        end_timestamp = self.date_to_timestamp(end_date)
        
        all_trades = []
        current_index_price = self.fetch_current_index_price()  # Fetch the current index price for moneyness calculation

        for ticker in tqdm(tickers, desc="Fetching data for tickers"):
            try:
                trades = self.get_trades_by_ticker(ticker, start_timestamp, end_timestamp)
                instrument_details = self.get_instrument_details(ticker)  # Get the strike, expiry, and option type
                
                if not instrument_details:
                    print(f"No details found for instrument: {ticker}")
                    continue
                
                strike_price = instrument_details['strike']
                expiry_date = instrument_details['expiry']
                option_type = instrument_details['option_type']
                moneyness = self.calculate_moneyness(strike_price, current_index_price, option_type)
                
                for trade in trades:
                    trade['instrument_name'] = ticker  # Add instrument name to each trade
                    trade['real_date'] = self.timestamp_to_date_string(trade['timestamp'])  # Convert timestamp to date string
                    trade['strike_price'] = strike_price  # Add strike price
                    trade['expiry_date'] = expiry_date  # Add expiry date
                    trade['option_type'] = option_type  # Add option type
                    trade['moneyness'] = moneyness  # Add moneyness
                    all_trades.append(trade)
            except Exception as e:
                print(e)
            time.sleep(1)  #let's avoid rate-limiting (the code will avoid sending too many requests in a short time, allowing smooth and compliant data query)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_trades)
        return df

    def filter_atm_put_options(self, df_trades):
        """
            df_trades (pd.DataFrame): The DataFrame containing option trade data.
            
        --> Returns: pd.DataFrame: A DataFrame containing only ATM put options (--> this needs more structuring)
        """
        # Filter for put options and ATM moneyness
        filtered_df = df_trades[(df_trades['option_type'] == 'put') & (df_trades['moneyness'] == 'ATM')]
        return filtered_df


    #DVOL FETCHING:
    # Function to fetch DVOL data for only BTC or ETH and we get the close values from the candlestick data:
    # Informatiion of the DVOL documentation in here: https://docs.deribit.com/#public-get_volatility_index_data

    def dvol(self, currency, start, end, resolution):

        """
        Fetch the DVOL (Deribit Volatility Index) 'close' values (real DVOL (if we can call it that way)) for a given
        currency (BTC or ETH) over a specified time period, with converted timestamps.
        
        Args:
            currency (str): The currency for which to fetch DVOL ('BTC', 'ETH', etc.).
            start (int): The start timestamp (in milliseconds).
            Start and end dates are excluded, meaning that the results stop at the previous day for each
            end (int): The end timestamp (in milliseconds).
            resolution (str): The time resolution ('1', '60', '3600', '43200', '1D').
        
        Returns:
            pd.DataFrame: A DataFrame containing the DVOL 'close' values with timestamps.
        """
        # Build the URL to fetch DVOL data
        url = f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={currency.lower()}&start_timestamp={start}&end_timestamp={end}&resolution={resolution}"
        
        # Make the request to the Deribit API
        response = requests.get(url)
        
        # Check if the response was successful
        if response.status_code != 200:
            raise Exception(f"Error fetching DVOL data: {response.status_code}")
        
        # Parse the result from the API response
        dvol_data = response.json().get('result', {}).get('data', [])
        
        # Convert the data into a DataFrame
        df = pd.DataFrame(dvol_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        
        # Convert the timestamp (in milliseconds) to a readable date format
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.rename(columns={'close': 'iv'}, inplace=True)
        
        # Return only the timestamp and 'close' values (the real DVOL values)
        return df[['timestamp', 'iv']]


    # NEW DVOL METHO FOR RECURRING TIMESTAMPS (GET MORE THAN 1000 DATA POINTS): 
    def dvol_test(self, currency, start, end, resolution):
        
        """
        Fetch the DVOL (Deribit Volatility Index) 'close' values (real DVOL (if we can call it that way)) for a given
        currency (BTC or ETH) over a specified time period, with converted timestamps.
        
        Args:
            currency (str): The currency for which to fetch DVOL ('BTC', 'ETH', etc.).
            start (str)
            end (str)
            resolution (str): The time resolution in seconds ('1' every second), '60' (each minute), '3600' (each hour), '43200' (every 12hours), '1D' (daily))
            Some of these resolutions are not supported.     
        Returns:
            pd.DataFrame: A DataFrame containing the DVOL 'close' values with timestamps.
        """
        # Converting the dates into timestamps:
        start_t = date_to_timestamp(start)
        end_t = date_to_timestamp(end)
        # Build the URL to fetch DVOL data
        url = f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={currency.lower()}&start_timestamp={start_t}&end_timestamp={end_t}&resolution={resolution}"
        
        # Make the request to the Deribit API
        response = requests.get(url)
        
        # Check if the response was successful
        if response.status_code != 200:
            raise Exception(f"Error fetching DVOL data: {response.status_code}")
        
        # Parse the result from the API response
        dvol_data = response.json().get('result', {}).get('data', [])
        
        # Convert the data into a DataFrame
        df_final = pd.DataFrame(dvol_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        current_start = df_final.timestamp[0]
        # Convert the timestamp (in milliseconds) to a readable date format
        df_final['timestamp'] = pd.to_datetime(df_final['timestamp'], unit='ms')
    
        # We make sure to get the normal dvol daataframe and store the start date it ends with and redo the same query process:

        while current_start > start_t:
            # Build the URL to fetch DVOL data
            url = f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={currency.lower()}&start_timestamp={start_t}&end_timestamp={current_start}&resolution={resolution}"
            
            # Make the request to the Deribit API
            response = requests.get(url)
            
            # Check if the response was successful
            if response.status_code != 200:
                raise Exception(f"Error fetching DVOL data: {response.status_code}")
            
            # Parse the result from the API response
            dvol_data_loop = response.json().get('result', {}).get('data', [])
        
            # Convert the timestamp (in milliseconds) to a readable date format
            df_loop = pd.DataFrame(dvol_data_loop, columns=['timestamp', 'open', 'high', 'low', 'close'])
            # Update the variable:
            current_start = df_loop.timestamp[0]
            df_loop['timestamp'] = pd.to_datetime(df_loop['timestamp'], unit='ms')

            #merge:
            df_final = pd.concat([df_loop,df_final], ignore_index=True)
            
            # display the dates it stopped at
            print(f'The data query stopped at: {timestamp_to_date_string(current_start)}')
        
        # Return only the timestamp and 'close' values (the real DVOL values)
        df_final.rename(columns={'close': 'iv'}, inplace=True)
        return df_final[['timestamp', 'iv']]


    # Function to fetch hourly ETH price data from Deribit
    def fetch_asset_price(start_date, end_date, asset, resolution):
        url = 'https://www.deribit.com/api/v2/public/get_tradingview_chart_data'
        
        # Convert dates to Unix timestamps (in milliseconds)
        start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp()) * 1000
        end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) * 1000
        
        # Fetch data in hourly resolution
        params = {
            'instrument_name': asset+'-PERPETUAL',
            'start_timestamp': start_timestamp,
            'end_timestamp': end_timestamp,
            'resolution': resolution  # 60-minute intervals for hourly data
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()['result']
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(data['ticks'], unit='ms'),
                'open': data['open'],
                'high': data['high'],
                'low': data['low'],
                'close': data['close'],
                'volume': data['volume']
            })
            return df
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None

