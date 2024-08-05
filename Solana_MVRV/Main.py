import pandas as pd
import requests
import matplotlib.pyplot as plt
import mplcursors
from datetime import datetime

# Load the CSV file
file_path = "C:/Users/Kalvika/Downloads/export_txs_6rwLZjzBKpNC4guCUXvMLvNnDH65GE2EGXLk6ZpB9N6w_1719604035621.csv"
data = pd.read_csv(file_path)

# Strip any leading/trailing spaces from column names
data.columns = data.columns.str.strip()

# Convert 'Date' column to datetime and keep only the date part
data['Date'] = pd.to_datetime(data['Date'], errors='coerce').dt.date

# Check the unique dates in the dataset to ensure they are parsed correctly
print("Unique dates in transaction data:\n", data['Date'].unique())

# Function to fetch historical prices from CoinMarketCap API
def fetch_historical_prices(api_key, symbol, start_date, end_date):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/historical'
    parameters = {
        'symbol': symbol,
        'convert': 'USD',
        'time_start': start_date,
        'time_end': end_date,
        'interval': 'daily'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    response = requests.get(url, headers=headers, params=parameters)
    response_json = response.json()
    if 'data' in response_json:
        quotes = response_json['data']['quotes']
        prices = {quote['timestamp'][:10]: quote['quote']['USD']['price'] for quote in quotes}
        return prices
    else:
        print("Error fetching data from CoinMarketCap API:\n", response_json)
        return None

# Fetch circulating supply and latest prices from CoinMarketCap API
def fetch_current_data(api_key, symbol):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    parameters = {
        'symbol': symbol,
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    response = requests.get(url, headers=headers, params=parameters)
    response_json = response.json()
    if 'data' in response_json:
        market_data = response_json['data'][symbol]
        circulating_supply = market_data['circulating_supply']
        latest_price = market_data['quote']['USD']['price']
        return circulating_supply, latest_price
    else:
        print("Error fetching data from CoinMarketCap API:\n", response_json)
        return None, None

# Define your API key and symbol
api_key = '83eb1fed-5bdf-4480-b12c-3b261ea89650'
symbol = 'SOL'
start_date = '2024-06-01T00:00:00Z'
end_date = '2024-07-01T00:00:00Z'

# Fetch current data
circulating_supply, latest_price = fetch_current_data(api_key, symbol)
print(f"Circulating supply: {circulating_supply}, Latest price: {latest_price}")

# Fetch historical prices
historical_prices = fetch_historical_prices(api_key, symbol, start_date, end_date)
if historical_prices is None:
    raise SystemExit

# Convert historical prices to DataFrame
prices_df = pd.DataFrame(list(historical_prices.items()), columns=['Date', 'price'])
prices_df['Date'] = pd.to_datetime(prices_df['Date']).dt.date
prices_df.set_index('Date', inplace=True)

# Check the unique dates in the historical prices to ensure they are parsed correctly
print("Unique dates in historical prices:\n", prices_df.index.unique())

# Merge with transaction data
merged_data = pd.merge(data, prices_df, on='Date', how='inner')

# Check the merged data to ensure it is correct
print("Merged data:\n", merged_data.head())

# Calculate realized value
spl_balance_change_col = 'SPL BalanceChange'
merged_data[spl_balance_change_col] = pd.to_numeric(merged_data[spl_balance_change_col], errors='coerce')
merged_data['value_moved'] = merged_data[spl_balance_change_col] * merged_data['price']

# Calculate daily market value and realized value
daily_market_value = merged_data.groupby('Date')['price'].apply(lambda x: x.iloc[-1] * circulating_supply)
daily_realized_value = merged_data.groupby('Date')['value_moved'].sum()
mvrv_ratio = daily_market_value / daily_realized_value

# Check the resulting DataFrames to ensure calculations are correct
print("MVRV Ratio: ", mvrv_ratio)
print("Daily market value:\n", daily_market_value)
print("Daily realized value:\n", daily_realized_value)

# Calculate MVRV Z-score
mean_mvrv = mvrv_ratio.mean()
std_mvrv = mvrv_ratio.std()
mvrv_z_score = (mvrv_ratio - mean_mvrv) / std_mvrv

# Print mean MVRV and standard deviation
print(f"Mean MVRV: {mean_mvrv}")
print(f"Standard Deviation MVRV: {std_mvrv}")

# Check the resulting DataFrames to ensure calculations are correct
print("MVRV Z-score:\n", mvrv_z_score)

# Plotting the graph
fig, ax1 = plt.subplots(figsize=(14, 7))

color = 'tab:blue'
ax1.set_xlabel('Date')
ax1.set_ylabel('MVRV Z-score', color=color)
zscore_line, = ax1.plot(mvrv_z_score.index, mvrv_z_score, color=color)
ax1.tick_params(axis='y', labelcolor=color)
ax1.set_ylim(-2, 2)

ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('Price (USD)', color=color)
price_line, = ax2.plot(prices_df.index, prices_df['price'], color=color)
ax2.tick_params(axis='y', labelcolor=color)
ax2.set_ylim(0, 200)

fig.tight_layout()

# Adding mplcursors for interactive tooltips
cursor = mplcursors.cursor(zscore_line, hover=True)
cursor.connect("add", lambda sel: sel.annotation.set_text(f"Date: {pd.to_datetime(mvrv_z_score.index[int(sel.index)]).strftime('%Y-%m-%d')}\nZ-score: {sel.target[1]:.2f}"))

cursor2 = mplcursors.cursor(price_line, hover=True)
cursor2.connect("add", lambda sel: sel.annotation.set_text(f"Date: {pd.to_datetime(prices_df.index[int(sel.index)]).strftime('%Y-%m-%d')}\nPrice: ${sel.target[1]:.2f}"))

plt.show()
