import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bitcoinrpc.authproxy import AuthServiceProxy
import datetime as dt
import requests

# Configuration for RPC connection
rpc_user = "KalvikaM"
rpc_password = "Magic@2023"
rpc_host = "127.0.0.1"
rpc_port = 18333
wallet_name = "uwallet"

# Establish RPC connection
def get_rpc_connection():
    return AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}/wallet/{wallet_name}")

# Attempt to connect to the RPC server
try:
    rpc_connection = get_rpc_connection()
except Exception as e:
    print(f"Failed to connect to Bitcoin RPC: {e}")
    rpc_connection = None

# Get historical price data from CryptoCompare
def get_historical_prices():
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    params = {
        'fsym': 'BTC',
        'tsym': 'USD',
        'limit': 730,  # Adjust the limit to get more historical data
        'api_key': 'ed32622eb0ccc7935e211f78ab6ec3778c2f6cf6f2650a06611b925d99a4eb9e'
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'Data' not in data or 'Data' not in data['Data']:
        print("Error fetching historical prices:", data)
        return {}

    prices = {dt.datetime.fromtimestamp(day['time'], dt.timezone.utc).strftime('%Y-%m'): day['close'] for day in data['Data']['Data']}
    return prices

# Get historical prices once
historical_prices = get_historical_prices()

# Function to get historical price for a specific date
def get_historical_price(date):
    return historical_prices.get(date, 30000)  # Default to 30000 if date not found

# Simulate UTXOs using historical data
def simulate_utxos():
    utxos = []
    for date, price in historical_prices.items():
        utxo = {
            'txid': f'simulated-{date}',
            'vout': 0,
            'value': 1.0,  # Assume 1 BTC for simplicity
            'time': int(dt.datetime.strptime(date, '%Y-%m').timestamp())
        }
        utxos.append(utxo)
    return utxos

# Calculate realized value using simulated UTXOs
def calculate_realized_value():
    utxos = simulate_utxos()
    realized_value = 0
    for utxo in utxos:
        timestamp = utxo['time']
        date = dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime('%Y-%m')
        last_moved_price = get_historical_price(date)
        realized_value += utxo['value'] * last_moved_price
    return realized_value

# Placeholder function to get current price
def get_current_price():
    url = "https://min-api.cryptocompare.com/data/price"
    params = {
        'fsym': 'BTC',
        'tsyms': 'USD',
        'api_key': 'ed32622eb0ccc7935e211f78ab6ec3778c2f6cf6f2650a06611b925d99a4eb9e'
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get('USD', 40000)  # Default to 40000 if the price is not found

# Calculate total supply of Bitcoin
def get_total_supply():
    try:
        block_count = rpc_connection.getblockcount()
    except Exception as e:
        print(f"Failed to get block count: {e}")
        return 21000000  # Assume max supply if unable to connect

    block_reward = 50
    total_supply = 0
    for height in range(block_count + 1):
        if height < 210000:
            reward = 50
        elif height < 420000:
            reward = 25
        elif height < 630000:
            reward = 12.5
        else:
            reward = 6.25
        total_supply += reward
    return total_supply

# Calculate market value
def calculate_market_value():
    current_price = get_current_price()
    total_supply = get_total_supply()
    market_value = current_price * total_supply
    return market_value

# Calculate MVRV ratio
def calculate_mvrv_ratio():
    market_value = calculate_market_value()
    realized_value = calculate_realized_value()
    if realized_value == 0:
        print("Realized value is zero, skipping MVRV ratio calculation.")
        return None
    mvrv_ratio = market_value / realized_value
    return mvrv_ratio

def main():
    # Example dates for the past two years
    dates = pd.date_range(start="2022-01-01", end="2024-01-01", freq='ME')
    mvrv_ratios = []
    
    for date in dates:
        historical_date = date.strftime('%Y-%m')
        market_value = get_total_supply() * get_historical_price(historical_date)
        realized_value = calculate_realized_value()
        if realized_value != 0:
            mvrv_ratio = market_value / realized_value
            mvrv_ratios.append(mvrv_ratio)
        else:
            print(f"Realized value is zero for date {historical_date}, skipping MVRV ratio calculation.")
    
    z_scores = calculate_z_score(mvrv_ratios)

    # Plotting the data
    fig, ax1 = plt.subplots(figsize=(14, 7))
    
    ax1.plot(dates[:len(z_scores)], z_scores, label="Bitcoin MVRV Z-Score", color='green')
    ax1.set_ylabel('Z-Score')
    ax1.set_ylim(-2, 12)
    ax1.axhline(0, color='grey', linewidth=0.5, linestyle='--')
    ax1.axhline(-2, color='grey', linewidth=0.5, linestyle='--')
    
    ax2 = ax1.twinx()
    btc_prices = [get_historical_price(date.strftime('%Y-%m')) for date in dates]
    ax2.plot(dates, btc_prices, label="BTC Price", color='orange')
    ax2.set_ylabel('BTC Price (USD)')
    
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.title('Bitcoin MVRV Z-Score and BTC Price (Monthly)')
    plt.grid(True)
    plt.show()

def calculate_z_score(values):
    mean = np.mean(values)
    std_dev = np.std(values)
    z_scores = [(value - mean) / std_dev for value in values]
    return z_scores

if __name__ == "__main__":
    main()
