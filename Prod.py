import streamlit as st
import yfinance as yf
import pandas as pd

# Function to check for Marubozu candlestick pattern with a percentage threshold
def is_marubozu(row, threshold=0.2):
    open_low_diff = abs(row['Open'] - row['Low'])
    high_close_diff = abs(row['High'] - row['Close'])
    open_low_pct = (open_low_diff / row['Low']) * 100
    high_close_pct = (high_close_diff / row['High']) * 100
    return open_low_pct <= threshold and high_close_pct <= threshold

# Function to check for Bullish Engulfing candlestick pattern
def is_bullish_engulfing(current_row, previous_row):
    if previous_row['Close'] < previous_row['Open'] and current_row['Close'] > current_row['Open'] \
            and current_row['Open'] < previous_row['Close'] and current_row['Close'] > previous_row['Open']:
        return True
    else:
        return False

# Function to check for Bullish Harami candlestick pattern
def is_bullish_harami(current_row, previous_row):
    if previous_row['Close'] < previous_row['Open'] and current_row['Close'] > current_row['Open'] \
            and current_row['Open'] > previous_row['Close'] and current_row['Close'] < previous_row['Open']:
        return True
    else:
        return False

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Dictionary for multiple username and password pairs
user_credentials = {
    "admin": "654987",
    "ezar": "654321",
    "shivam": "986532"
}

# Sign-in form
def signin():
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign In"):
        if username in user_credentials and user_credentials[username] == password:
            st.session_state.authenticated = True
        else:
            st.sidebar.error("Invalid username or password")

# Sign-out button
def signout():
    if st.sidebar.button("Sign Out"):
        st.session_state.authenticated = False

# Main application
if st.session_state.authenticated:
    st.title("Indian Stock Data Viewer")

    # Sidebar for user input
    tickers = st.sidebar.text_input("Enter the ticker symbols separated by commas", "RELIANCE.NS, TCS.NS, INFY.NS")
    start_date = st.sidebar.date_input("Start date", pd.to_datetime("2024-06-01"))
    end_date = st.sidebar.date_input("End date", pd.to_datetime("2024-06-14"))
    marubozu_threshold = st.sidebar.number_input("Marubozu threshold (%)", min_value=0.0, max_value=5.0, value=0.2)

    # Candlestick pattern filter (optional)
    patterns = st.sidebar.multiselect(
        "Select candlestick patterns to filter by (optional)",
        options=['Marubozu', 'Bullish Engulfing', 'Bullish Harami']
    )

    # Fetch stock data
    if st.sidebar.button("Fetch Data"):
        tickers_list = [ticker.strip() for ticker in tickers.split(",")]

        all_stock_data = pd.DataFrame()

        for ticker_symbol in tickers_list:
            try:
                # Download the stock data
                stock_data = yf.download(ticker_symbol, start=start_date, end=end_date, interval='1d')

                if not stock_data.empty:
                    # Get stock info to fetch the stock name
                    stock_info = yf.Ticker(ticker_symbol).info
                    stock_name = stock_info.get("shortName", ticker_symbol)

                    # Shift the data to get the previous day's data
                    stock_data['Prev Open'] = stock_data['Open'].shift(1)
                    stock_data['Prev Close'] = stock_data['Close'].shift(1)

                    # Check for Marubozu candlesticks
                    stock_data['Marubozu'] = stock_data.apply(is_marubozu, axis=1, threshold=marubozu_threshold)

                    # Check for Bullish Engulfing candlesticks
                    stock_data['Bullish Engulfing'] = stock_data.apply(
                        lambda row: is_bullish_engulfing(row, stock_data.loc[row.name - pd.Timedelta(days=1)])
                        if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1
                    )

                    # Check for Bullish Harami candlesticks
                    stock_data['Bullish Harami'] = stock_data.apply(
                        lambda row: is_bullish_harami(row, stock_data.loc[row.name - pd.Timedelta(days=1)])
                        if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1
                    )

                    stock_data['Stock Name'] = stock_name  # Add stock name to the DataFrame

                    # Append the stock data to the main DataFrame
                    all_stock_data = pd.concat([all_stock_data, stock_data])
                else:
                    st.warning(f"No data found for the ticker symbol {ticker_symbol} and the given date range")
            except Exception as e:
                st.error(f"Error fetching data for {ticker_symbol}: {e}")

        if not all_stock_data.empty:
            if patterns:
                # Filter the data based on selected patterns
                filter_condition = pd.Series([False] * len(all_stock_data), index=all_stock_data.index)
                if 'Marubozu' in patterns:
                    filter_condition |= all_stock_data['Marubozu']
                if 'Bullish Engulfing' in patterns:
                    filter_condition |= all_stock_data['Bullish Engulfing']
                if 'Bullish Harami' in patterns:
                    filter_condition |= all_stock_data['Bullish Harami']

                filtered_stock_data = all_stock_data[filter_condition]
            else:
                filtered_stock_data = all_stock_data

            # Display the filtered stock data
            st.subheader("Filtered Stock Data")
            st.dataframe(filtered_stock_data[['Stock Name', 'Open', 'High', 'Low', 'Close', 'Marubozu', 'Bullish Engulfing', 'Bullish Harami']])
        else:
            st.error("No data found for the given ticker symbols and date range")

    # Sign-out button
    signout()
else:
    signin()

# Run the app using: streamlit run your_script_name.py
