import os
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def fetch_historical_prices(ticker):
    """Fetch historical prices from Yahoo Finance, caching if less than 1 day old."""
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
    """Simulate a single future price path using the Black-Scholes model."""
    dt = 1 / 365  # Daily time increment
    prices = [start_price]
    
    for _ in range(days):
        price_t = prices[-1]
        # Simulate the next price with annualized parameters
        price_t1 = price_t * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * np.random.normal())
        prices.append(price_t1)

    return prices

def main(ticker, simulations=500):
    # Fetch historical prices
    historical_data = fetch_historical_prices(ticker)
    
    # Calculate daily returns
    historical_data['Return'] = historical_data['Adj Close'].pct_change()
    daily_mu = historical_data['Return'].mean()
    daily_sigma = historical_data['Return'].std()

    # Annualize the mean and standard deviation
    mu = daily_mu * 252  # Assuming 252 trading days in a year
    sigma = daily_sigma * np.sqrt(252)

    # Get the last price
    start_price = historical_data['Adj Close'][-1]

    # Run multiple simulations and store paths
    all_simulated_prices = [black_scholes_simulation(start_price, mu, sigma) for _ in range(simulations)]
    all_simulated_prices = np.array(all_simulated_prices)

    # Calculate the mean path and standard deviations across simulations
    mean_path = all_simulated_prices.mean(axis=0)
    std_dev_path = all_simulated_prices.std(axis=0)
    upper_2std_bound = mean_path + 2 * std_dev_path
    lower_2std_bound = mean_path - 2 * std_dev_path
    upper_1std_bound = mean_path + std_dev_path
    lower_1std_bound = mean_path - std_dev_path

    # Plot each path with conditional coloring
    plt.figure(figsize=(12, 8))
    for prices in all_simulated_prices:
        final_price = prices[-1]
        mean_final_price = mean_path[-1]
        upper_1std_final_price = mean_path[-1] + std_dev_path[-1]
        lower_1std_final_price = mean_path[-1] - std_dev_path[-1]
        upper_2std_final_price = mean_path[-1] + 2 * std_dev_path[-1]
        lower_2std_final_price = mean_path[-1] - 2 * std_dev_path[-1]

        # Determine color based on final price
        if final_price > upper_2std_final_price or final_price < lower_2std_final_price:
            color = 'grey'  # More than 2 std devs from the mean
        elif final_price > upper_1std_final_price:
            color = 'lightgreen'  # Between 1 and 2 std devs above the mean
        elif final_price < lower_1std_final_price:
            color = 'lightcoral'  # Between 1 and 2 std devs below the mean
        elif final_price > mean_final_price:
            color = 'darkgreen'  # Above mean but within 1 std dev
        else:
            color = 'darkred'  # Below mean but within 1 std dev
        
        plt.plot(prices, color=color, alpha=0.6)

    # Plot the mean path in thick white
    plt.plot(mean_path, color='white', label='Mean Path', linewidth=2.5)

    # Plot the upper and lower bounds (± 2 std devs) in thick blue
    plt.plot(upper_2std_bound, color='blue', linestyle='--', label='Upper Bound (Mean + 2 Std Dev)', linewidth=2)
    plt.plot(lower_2std_bound, color='blue', linestyle='--', label='Lower Bound (Mean - 2 Std Dev)', linewidth=2)

    # Plot the upper and lower bounds (± 1 std dev) in thin cyan
    plt.plot(upper_1std_bound, color='cyan', linestyle='--', label='Upper Bound (Mean + 1 Std Dev)', linewidth=1)
    plt.plot(lower_1std_bound, color='cyan', linestyle='--', label='Lower Bound (Mean - 1 Std Dev)', linewidth=1)

    # Plotting settings
    plt.title(f'{simulations} Simulated Price Paths for {ticker} over Next 365 Days')
    plt.xlabel('Days')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.show()

if __name__ == "__main__":
    ticker = input("Enter the stock ticker symbol: ")
    main(ticker)