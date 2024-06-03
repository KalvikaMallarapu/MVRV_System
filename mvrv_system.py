import pandas as pd
import requests
import matplotlib.pyplot as plt

def fetch_market_data(crypto_symbol):
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={crypto_symbol.upper()}&tsym=USD&limit=2000"
    response = requests.get(url)
    
    # Debugging output to understand the problem
    print(f"Request URL: {url}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text[:500]}")  # Print the first 500 characters of the response text
    
    if response.status_code != 200:
        raise Exception(f"Error fetching data from API. Status code: {response.status_code}")
    
    data = response.json()
    if 'Data' not in data or 'Data' not in data['Data']:
        raise KeyError("'Data' not found in the API response.")
    
    prices = [(item['time']*1000, item['close']) for item in data['Data']['Data']]
    return prices

def fetch_realized_value_data(crypto_symbol):
    # This function should fetch realized value data. As a placeholder, using the same market data.
    # In reality, you would need an API that provides realized value data.
    return fetch_market_data(crypto_symbol)

def calculate_mvrv(market_data, realized_value_data):
    market_df = pd.DataFrame(market_data, columns=['timestamp', 'market_value'])
    realized_df = pd.DataFrame(realized_value_data, columns=['timestamp', 'realized_value'])
    
    market_df['timestamp'] = pd.to_datetime(market_df['timestamp'], unit='ms')
    realized_df['timestamp'] = pd.to_datetime(realized_df['timestamp'], unit='ms')
    
    merged_df = pd.merge(market_df, realized_df, on='timestamp', suffixes=('_market', '_realized'))
    merged_df['mvrv_ratio'] = merged_df['market_value'] / merged_df['realized_value']
    
    return merged_df

def plot_mvrv(mvrv_data):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot MVRV Ratio
    ax.plot(mvrv_data['timestamp'], mvrv_data['mvrv_ratio'], label='MVRV Ratio', color='blue')
    
    # Plot Moving Average
    mvrv_data['mvrv_ratio_ma'] = mvrv_data['mvrv_ratio'].rolling(window=30).mean()
    ax.plot(mvrv_data['timestamp'], mvrv_data['mvrv_ratio_ma'], label='30-Day Moving Average', color='red', linestyle='--')
    
    # Add Annotations
    max_mvr = mvrv_data['mvrv_ratio'].max()
    max_mvr_date = mvrv_data.loc[mvrv_data['mvrv_ratio'].idxmax(), 'timestamp']
    ax.annotate(f'Max MVRV Ratio ({max_mvr:.2f})', xy=(max_mvr_date, max_mvr), xytext=(-80, 20),
                textcoords='offset points', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2"))

    min_mvr = mvrv_data['mvrv_ratio'].min()
    min_mvr_date = mvrv_data.loc[mvrv_data['mvrv_ratio'].idxmin(), 'timestamp']
    ax.annotate(f'Min MVRV Ratio ({min_mvr:.2f})', xy=(min_mvr_date, min_mvr), xytext=(-80, -30),
                textcoords='offset points', arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.2"))
    
    # Customize Plot
    ax.set_xlabel('Date')
    ax.set_ylabel('MVRV Ratio')
    ax.set_title('MVRV Ratio Over Time')
    ax.legend()
    
    plt.tight_layout()
    plt.show()

def main():
    crypto_symbol = 'BTC'  # Example: 'BTC', 'ETH'
    market_data = fetch_market_data(crypto_symbol)
    realized_value_data = fetch_realized_value_data(crypto_symbol)
    mvrv_data = calculate_mvrv(market_data, realized_value_data)
    plot_mvrv(mvrv_data)

if __name__ == "__main__":
    main()
