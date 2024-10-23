import os
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def fetch_historical_prices(ticker):
    """Fetch historical prices from Yahoo Finance."""
    today = datetime.now().date()
    file_name = f"{ticker}_historical_prices.csv"

    # Check if the file exists and its age
    if os.path.exists(file_name):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_name)).date()
        if (today - file_mod_time) < timedelta(days=1):
            print(f"Using cached data from {file_name}")
            return pd.read_csv(file_name, index_col=0, parse_dates=True)

    # Fetch the data if file is older than 1 day or does not exist
    print(f"Fetching new data for {ticker}...")
    data = yf.download(ticker, start='2020-01-01', end=today)
    
    # Save to a CSV file
    data.to_csv(file_name)
    return data

def black_scholes_simulation(start_price, mu, sigma, days=365):
    """Simulate future price paths using the Black-Scholes model."""
    dt = 1 / 365  # Daily time increment
    prices = [start_price]
    
    for _ in range(days):
        price_t = prices[-1]
        # Simulate the next price
        price_t1 = price_t * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * np.random.normal())
        prices.append(price_t1)

    return prices

def main(ticker, simulations=500):
    # Fetch historical prices
    historical_data = fetch_historical_prices(ticker)
    
    # Calculate daily returns
    historical_data['Return'] = historical_data['Adj Close'].pct_change()
    mu = historical_data['Return'].mean()
    sigma = historical_data['Return'].std()

    # Get the last price
    start_price = historical_data['Adj Close'][-1]

    # Initialize a list to store simulated price paths
    all_simulated_prices = []

    # Run multiple simulations
    for _ in range(simulations):
        simulated_prices = black_scholes_simulation(start_price, mu, sigma)
        all_simulated_prices.append(simulated_prices)

    # Convert to a numpy array for easier manipulation
    all_simulated_prices = np.array(all_simulated_prices)

    # Calculate the mean and standard deviation of the simulated paths
    mean_path = all_simulated_prices.mean(axis=0)
    std_dev = all_simulated_prices.std(axis=0)

    # Calculate the upper and lower bounds (mean ± 2 standard deviations)
    upper_bound = mean_path + 2 * std_dev
    lower_bound = mean_path - 2 * std_dev

    # Initialize a plot
    plt.figure(figsize=(12, 8))

    # Plot all simulated paths
    for prices in all_simulated_prices:
        plt.plot(prices, color='lightblue', alpha=0.1)

    # Plot the mean path
    plt.plot(mean_path, color='blue', label='Mean Path', linewidth=2)

    # Plot the upper and lower bounds
    plt.plot(upper_bound, color='red', linestyle='--', label='Upper Bound (Mean + 2 Std Dev)', linewidth=2)
    plt.plot(lower_bound, color='green', linestyle='--', label='Lower Bound (Mean - 2 Std Dev)', linewidth=2)

    # Plotting settings
    plt.title(f'Simulated Price Paths for {ticker} (500 Simulations)')
    plt.xlabel('Days')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.show()

if __name__ == "__main__":
    ticker = input("Enter the stock ticker symbol: ")
    main(ticker)
