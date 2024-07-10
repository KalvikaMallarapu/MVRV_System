import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplcursors

# Constants
API_KEY_NEW = '83eb1fed-5bdf-4480-b12c-3b261ea89650'
HISTORICAL_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical'
BLOCKCHAIR_API_KEY = 'A___RPbAky67IXr4PQtXb4xerP1Tzgq6'
WALLET_ADDRESS = '1Ay8vMC7R1UbyCCZRVULMV7iQpHSAbguJP'
symbol = 'BTC'
start_date = '2024-05-01T00:00:00Z'
end_date = '2024-06-01T00:00:00Z'

# Parameters and headers for the CoinMarketCap API request
params = {
    'symbol': symbol,
    'time_start': start_date,
    'time_end': end_date,
    'interval': 'daily'
}

headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': API_KEY_NEW
}

# Fetch historical BTC prices
response = requests.get(HISTORICAL_URL, headers=headers, params=params)
btc_data = response.json()

# Extract prices and create DataFrame
prices = []
for quote in btc_data['data']['quotes']:
    prices.append({
        'date': quote['timestamp'],
        'price': quote['quote']['USD']['price'],
        'circulating_supply': quote['quote']['USD'].get('circulating_supply')
    })

prices_df = pd.DataFrame(prices)
prices_df['date'] = pd.to_datetime(prices_df['date']).dt.tz_localize(None)
prices_df.set_index('date', inplace=True)

# Ensure prices_df contains all necessary dates
all_dates = pd.date_range(start=prices_df.index.min(), end=prices_df.index.max(), freq='D')
prices_df = prices_df.reindex(all_dates).ffill()

# Fetch UTXO data for the wallet address
blockchair_url = f'https://api.blockchair.com/bitcoin/dashboards/address/{WALLET_ADDRESS}?key={BLOCKCHAIR_API_KEY}'
utxo_response = requests.get(blockchair_url)

if utxo_response.status_code == 200:
    utxo_data = utxo_response.json()['data'][WALLET_ADDRESS]['utxo']
    utxo_df = pd.DataFrame(utxo_data)
else:
    print("Error fetching UTXO data:", utxo_response.json())
    utxo_data = []

# Ensure there are UTXOs to process
if not utxo_data:
    raise Exception("No UTXO data available to process")

# Mock block times for UTXO if not present
utxo_df['block_time'] = pd.to_datetime('2024-05-01') + pd.to_timedelta(utxo_df.index, unit='d')

# Read the wallet statement CSV file
file_path = r"C:\Users\Kalvika\Downloads\Wallet statement 1_1 2024-05-01 - 2024-06-01 (1).csv"
wallet_df = pd.read_csv(file_path, sep=';', header=None, skiprows=11)
wallet_df.columns = ['Tx number', 'Address', 'Effect', 'Ticker', 'Amount fiat (USD)', 'Asset rate (USD)', 'Date', 'Transaction hash']
wallet_df['Date'] = pd.to_datetime(wallet_df['Date'].str.replace('"', '')).dt.tz_localize(None)
wallet_df['Amount fiat (USD)'] = wallet_df['Amount fiat (USD)'].astype(float)
wallet_df['Asset rate (USD)'] = wallet_df['Asset rate (USD)'].astype(float)

# Merge UTXO DataFrame with wallet statement to get asset rates
merged_df = pd.merge(utxo_df, wallet_df, left_on='block_time', right_on='Date', how='left')

# Calculate Realized Value using the "Asset rate (USD)" from the CSV file
realized_value = 0
print("Realized Value Calculations:")
for index, row in merged_df.iterrows():
    amount = row['value'] / 1e8  # Convert satoshi to BTC
    if not pd.isna(row['Asset rate (USD)']):
        price = row['Asset rate (USD)']
    else:
        # Align block_time to match the index format in prices_df
        aligned_time = row['block_time'].normalize()
        if aligned_time in prices_df.index:
            price = prices_df.loc[aligned_time, 'price']
        else:
            print(f"Price data not available for date: {aligned_time}")
            continue
    value = amount * price
    realized_value += value
    print(f"UTXO {index + 1}: {amount:.8f} BTC * {price:.2f} USD = {value:.2f} USD")

print(f"\nTotal Realized Value: {realized_value:.2f} USD")

# Calculate Market Value (MV) using circulating supply and daily BTC prices from the API
prices_df['MV'] = prices_df['circulating_supply'] * prices_df['price']

print("\nMarket Value Calculations:")
for date, row in prices_df.iterrows():
    mv = row['MV']
    print(f"Date: {date.strftime('%Y-%m-%d')} - Circulating Supply: {row['circulating_supply']} BTC * Price: {row['price']:.2f} USD = MV: {mv:.2f} USD")

# Filter dates where all values are available
valid_dates = prices_df.dropna().index

# Calculate MVRV ratio
mvrv_ratio = prices_df.loc[valid_dates]['MV'] / realized_value

# Calculate Mean and Standard Deviation of MVRV ratio
mean_mvrv = mvrv_ratio.mean()
std_mvrv = mvrv_ratio.std()

# Calculate MVRV Z-score
prices_df.loc[valid_dates, 'MVRV Z-score'] = (mvrv_ratio - mean_mvrv) / std_mvrv

# Print the MVRV Z-scores
print("\nMVRV Z-scores:")
print(prices_df['MVRV Z-score'])

# Plotting
fig, ax1 = plt.subplots(figsize=(12, 6))

# Plotting BTC Price
color = 'tab:red'
ax1.set_xlabel('Date')
ax1.set_ylabel('BTC Price (USD)', color=color)
price_line, = ax1.plot(prices_df.index, prices_df['price'], label='BTC Price', color=color)
ax1.tick_params(axis='y', labelcolor=color)
ax1.legend(loc='upper left')
ax1.set_ylim(10000, 80000)  # Set the y-axis limit for BTC price

# Creating a second y-axis for MVRV Z-score
ax2 = ax1.twinx()
color = 'tab:blue'
ax2.set_ylabel('MVRV Z-score', color=color)
zscore_line, = ax2.plot(prices_df.loc[valid_dates].index, prices_df.loc[valid_dates, 'MVRV Z-score'], label='MVRV Z-score', color=color)
ax2.tick_params(axis='y', labelcolor=color)
ax2.legend(loc='upper right')
ax2.set_ylim(-2, 3)  # Set the y-axis limit for MVRV Z-score

# Adding mplcursors for interactive tooltips
cursor_price = mplcursors.cursor(price_line, hover=True)
cursor_price.connect("add", lambda sel: sel.annotation.set_text(f"Date: {prices_df.index[int(sel.index)].strftime('%Y-%m-%d')}\nPrice: ${sel.target[1]:.2f}"))

cursor_zscore = mplcursors.cursor(zscore_line, hover=True)
cursor_zscore.connect("add", lambda sel: sel.annotation.set_text(f"Date: {prices_df.loc[valid_dates].index[int(sel.index)].strftime('%Y-%m-%d')}\nMVRV Z-score: {sel.target[1]:.2f}"))

plt.title('BTC Price and MVRV Z-score over Time')
plt.grid(True)
plt.show()
