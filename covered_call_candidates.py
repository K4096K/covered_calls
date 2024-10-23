import os
import json
import requests
import pandas as pd  # Importing pandas for Excel operations
from datetime import datetime, timedelta
from tabulate import tabulate

# Constants
API_URL_OPTIONS = "https://finnhub.io/api/v1/stock/option-chain"
API_URL_QUOTE = "https://finnhub.io/api/v1/quote"
API_KEY_FILE = "apikey.txt"
DATA_DIR = "options_data"
MAX_EXPIRATION_MONTHS = 6
TOP_CANDIDATES = 10  # Limit to top 10 candidates
DELTA_MIN = 0.40     # Minimum delta threshold
DELTA_MAX = 0.70     # Maximum delta threshold
IV_MIN = 20          # Minimum implied volatility threshold (in %)
OPEN_INTEREST_MIN = 100  # Minimum open interest for liquidity
VOLUME_MIN = 100         # Minimum volume for activity
STRIKE_PROXIMITY = 0.1  # Maximum percentage difference from current price

# Function to read API key from file
def read_api_key():
    with open(API_KEY_FILE, 'r') as file:
        return file.read().strip()

# Function to get options chain data
def get_options_chain(ticker):
    api_key = read_api_key()
    params = {
        'symbol': ticker,
        'token': api_key
    }
    response = requests.get(API_URL_OPTIONS, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching options data: {response.status_code} - {response.text}")
        return None

# Function to get the current market price
def get_current_price(ticker):
    api_key = read_api_key()
    params = {
        'symbol': ticker,
        'token': api_key
    }
    response = requests.get(API_URL_QUOTE, params=params)

    if response.status_code == 200:
        quote_data = response.json()
        return quote_data['c']  # Current price
    else:
        print(f"Error fetching current price: {response.status_code} - {response.text}")
        return None

# Function to save data to a JSON file
def save_data(ticker, data):
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    file_path = os.path.join(DATA_DIR, f"{ticker}_options.json")
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file)
    
    print(f"Data saved to {file_path}")

# Function to check if the file is outdated
def is_file_outdated(ticker):
    file_path = os.path.join(DATA_DIR, f"{ticker}_options.json")
    if os.path.exists(file_path):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if datetime.now() - file_mod_time < timedelta(hours=4):
            return False  # File is not outdated
    return True  # File does not exist or is outdated

# Function to calculate score based on Greeks and other parameters
def calculate_score(delta, theta, gamma, open_interest, implied_volatility):
    # Score calculations based on delta, theta, gamma, open interest, and implied volatility
    score_delta = max(0, min((delta - 0.4) / 0.3 * 100, 100) if delta <= 0.7 else 100)
    score_theta = max(0, min(theta * 100, 100))  # Assume theta is a positive value
    score_gamma = max(0, min((gamma - 0.1) / 0.2 * 100, 100) if gamma <= 0.3 else 100)
    score_oi = max(0, min((open_interest - 100) / 900 * 100, 100))
    score_iv = max(0, min((implied_volatility - 20) / 80 * 100, 100))

    # Final score calculation as an average of the individual scores
    final_score = (score_delta + score_theta + score_gamma + score_oi + score_iv) / 5
    return final_score

# Function to analyze the options chain for covered call strategy
def analyze_covered_call(ticker, market_price):
    options_data = get_options_chain(ticker)
    
    if not options_data or 'data' not in options_data:
        return []

    calls = []
    for option in options_data['data']:
        expiration_date = option['expirationDate']
        expiration = datetime.strptime(expiration_date, "%Y-%m-%d")

        # Filter for options expiring within the next 6 months
        if expiration <= datetime.now() + timedelta(days=MAX_EXPIRATION_MONTHS * 30):
            for call in option['options']['CALL']:
                strike = call['strike']
                bid = call['bid']
                ask = call['ask']
                delta = call['delta']
                iv = call['impliedVolatility'] * 100  # Convert to percentage
                open_interest = call['openInterest']
                volume = call['volume']
                theta = call['theta']  # Assume theta is provided in the data
                gamma = call['gamma']  # Assume gamma is provided in the data
                contract_name = call['contractName']  # Get the contract name

                # Calculate the percentage difference between strike price and market price
                price_diff_percentage = abs(strike - market_price) / market_price

                # Apply filters based on delta, implied volatility, volume, open interest, and strike proximity
                if (DELTA_MIN <= delta <= DELTA_MAX and 
                    iv >= IV_MIN and 
                    open_interest >= OPEN_INTEREST_MIN and 
                    volume >= VOLUME_MIN and 
                    price_diff_percentage <= STRIKE_PROXIMITY):  # Check if the strike is within 10% of market price
                    
                    # Calculate median price
                    median_price = (bid + ask) / 2
                    # Calculate profit if exercised
                    profit_if_exercised = (median_price * 100) + (strike * 100 - market_price * 100)
                    # Calculate profit if not exercised (premium only)
                    profit_if_not_exercised = median_price * 100

                    # Calculate score based on Greeks
                    score = calculate_score(delta, theta, gamma, open_interest, iv)

                    calls.append({
                        'contract_name': contract_name,  # Store the contract name
                        'expiration': expiration,
                        'strike': strike,
                        'bid': bid,
                        'ask': ask,
                        'median_price': median_price,
                        'profit_if_exercised': profit_if_exercised,
                        'profit_if_not_exercised': profit_if_not_exercised,
                        'delta': delta,
                        'iv': iv,
                        'open_interest': open_interest,
                        'volume': volume,
                        'theta': theta,  # Add theta
                        'gamma': gamma,  # Add gamma
                        'score': score   # Add score
                    })
    
    # Sort calls by score and then by maximum profit if exercised
    sorted_calls = sorted(calls, key=lambda x: (x['score'], x['profit_if_exercised']), reverse=True)[:TOP_CANDIDATES]
    return sorted_calls

# Function to export analyzed data to Excel
def export_to_excel(ticker, analyzed_calls):
    excel_file_path = os.path.join(DATA_DIR, f"{ticker}_options.xlsx")
    
    # Create a DataFrame from the analyzed calls
    df = pd.DataFrame([{
        "Contract": call['contract_name'],
        "Exp": call['expiration'].strftime('%Y-%m-%d'),
        "Strike": call['strike'],
        "Bid": round(call['bid'], 2),
        "Ask": round(call['ask'], 2),
        "Med. Price": round(call['median_price'] * 100, 2),  # Median Price (x100)
        "P (exercised)": round(call['profit_if_exercised'], 2),
        "P (not exercised)": round(call['profit_if_not_exercised'], 2),
        "Vol": call['volume'],
        "O. Interest": call['open_interest'],
        "Score": round(call['score'], 2)
    } for call in analyzed_calls])
    
    # Save the DataFrame to an Excel file
    df.to_excel(excel_file_path, index=False)
    print(f"Data exported to {excel_file_path}")

# Main function
def main(ticker):
    if is_file_outdated(ticker):
        print(f"Fetching new data for {ticker}...")
        options_data = get_options_chain(ticker)
        if options_data:
            save_data(ticker, options_data)
    else:
        print(f"Using cached data for {ticker}.")

    # Get current market price
    market_price = get_current_price(ticker)

    if market_price is None:
        print("Could not retrieve current market price. Exiting.")
        return

    print(f"Current market price of {ticker}: ${market_price:.2f}")

    # Analyze options chain
    analyzed_calls = analyze_covered_call(ticker, market_price)

    # Display results in a table
    if analyzed_calls:
        table_data = []
        for call in analyzed_calls:
            table_data.append([
                call['contract_name'],              # Contract Name
                call['expiration'].strftime('%Y-%m-%d'),
                call['strike'],
                round(call['bid'], 2),
                round(call['ask'], 2),
                round(call['median_price'] * 100, 2),  # Median Price (x100)
                round(call['profit_if_exercised'], 2),
                round(call['profit_if_not_exercised'], 2),
                call['volume'],                    # Add volume to the table
                call['open_interest'],              # Add open interest to the table
                round(call['score'], 2)             # Add score to the table
            ])
        
        headers = ["Contract", "Exp", "Strike", "Bid", "Ask", "Med. Price", "P (exercised)", "P (not exercised)", "Vol", "O. Interest", "Score"]
        print(tabulate(table_data, headers=headers, floatfmt=".2f", tablefmt="grid"))

        # Export to Excel
        export_to_excel(ticker, analyzed_calls)  # Call the export function
    else:
        print("No suitable call options found.")

if __name__ == "__main__":
    ticker_symbol = input("Enter the ticker symbol: ").strip().upper()
    main(ticker_symbol)
