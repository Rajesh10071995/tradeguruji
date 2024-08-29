import streamlit as st
import yfinance as yf
import pandas as pd

# Define candlestick pattern functions
def is_marubozu(row, threshold=0.2):
    open_low_diff = abs(row['Open'] - row['Low'])
    high_close_diff = abs(row['High'] - row['Close'])
    open_low_pct = (open_low_diff / row['Low']) * 100
    high_close_pct = (high_close_diff / row['High']) * 100
    return open_low_pct <= threshold and high_close_pct <= threshold

def is_bullish_engulfing(current_row, previous_row):
    return (previous_row['Close'] < previous_row['Open'] and 
            current_row['Close'] > current_row['Open'] and 
            current_row['Open'] < previous_row['Close'] and 
            current_row['Close'] > previous_row['Open'])

def is_bearish_engulfing(current_row, previous_row):
    return (previous_row['Close'] > previous_row['Open'] and 
            current_row['Close'] < current_row['Open'] and 
            current_row['Open'] > previous_row['Close'] and 
            current_row['Close'] < previous_row['Open'])

def is_bullish_harami(current_row, previous_row):
    return (previous_row['Close'] < previous_row['Open'] and 
            current_row['Close'] > current_row['Open'] and 
            current_row['Open'] > previous_row['Close'] and 
            current_row['Close'] < previous_row['Open'])

def is_bearish_harami(current_row, previous_row):
    return (previous_row['Close'] > previous_row['Open'] and 
            current_row['Close'] < current_row['Open'] and 
            current_row['Open'] < previous_row['Close'] and 
            current_row['Close'] > previous_row['Open'])

def is_bearish_marubozu(row, threshold=0.2):
    open_high_diff = abs(row['Open'] - row['High'])
    low_close_diff = abs(row['Low'] - row['Close'])
    open_high_pct = (open_high_diff / row['High']) * 100
    low_close_pct = (low_close_diff / row['Low']) * 100
    return open_high_pct <= threshold and low_close_pct <= threshold

def get_opening_type(row):
    if row['Open'] > row['Prev Close']:
        return "Gap Up"
    elif row['Open'] < row['Prev Close']:
        return "Gap Down"
    else:
        return "Flat"

def get_signal(row):
    if row['Volume'] > 1.3 * row['Avg Volume']:
        if row['Bullish Engulfing'] or row['Marubozu'] or row['Bullish Harami']:
            return "Buy"
    elif row['Volume'] < 0.3 * row['Avg Volume']:
        if row['Bearish Engulfing'] or row['Bearish Marubozu'] or row['Bearish Harami']:
            return "Sell"
    return ""

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Dictionary for multiple username and password pairs
user_credentials = {
    "admin": "654987",
    "raja": "858585",
    "ezar": "654321"
}

# Authentication
def signin():
    st.markdown("<h1 style='text-align: center; color: #fc0606;'>Welcome to Stock Market Analysis</h1>", unsafe_allow_html=True)
    username = st.text_input("Username", key='signin_username')
    password = st.text_input("Password", type="password", key='signin_password')
    if st.button("Sign In"):
        if user_credentials.get(username) == password:
            st.session_state.authenticated = True
        else:
            st.error("Invalid username or password")
    st.markdown("<h5 style='text-align: center; color: black;'>We are not SEBI Registered Advisors. This website is purely for training and educational purposes. We shall not be responsible for your profit or loss. Please confirm with your investment advisor. Futures, stocks and options trading involves substantial risk of loss and is not suitable for every investor. The valuation of futures, stocks and options may fluctuate, and, as a result, clients may lose more than their original investment. The impact of seasonal and geopolitical events is already factored into market prices. The highly leveraged nature of futures trading means that small market movements will have a great impact on your trading account and this can work against you, leading to large losses or can work for you, leading to large gains. If the market moves against you, you may sustain a total loss greater than the amount you deposited into your account. You are responsible for all the risks and financial resources you use and for the chosen trading system. You should not engage in trading unless you fully understand the nature of the transactions you are entering into and the extent of your exposure to loss. If you do not fully understand these risks you must seek independent advice from your financial advisor. All trading strategies are used at your own risk.</h5>", unsafe_allow_html=True)

def signout():
    if st.sidebar.button("Sign Out"):
        st.session_state.authenticated = False

# Main application
if st.session_state.authenticated:
    st.markdown("<h3 style='text-align: center; color: #f90606;'>Rajesh ka Stock Ananlysis</h3>", unsafe_allow_html=True)
    st.sidebar.markdown("<h1 style='text-align: center; color: #fc0606;'>Stock Data Filters</h1>", unsafe_allow_html=True)

    with st.sidebar.container():
        tickers_input = st.text_input("Enter the ticker symbols separated by commas (optional)")
        start_date = st.date_input("Start date", pd.to_datetime("2024-06-01"))
        end_date = st.date_input("End date", pd.to_datetime("today"))
        marubozu_threshold = st.number_input("Marubozu threshold (%)", min_value=0.0, max_value=5.0, value=0.2)
        patterns = st.multiselect("Select candlestick patterns to filter by (optional)",
                                  options=['Marubozu', 'Bullish Engulfing', 'Bearish Engulfing', 'Bullish Harami', 'Bearish Harami', 'Bearish Marubozu'])
        signal_filter = st.multiselect("Select signals to filter by (optional)", options=['Buy', 'Sell'])
        st.markdown("<hr>", unsafe_allow_html=True)

    if st.sidebar.button("Fetch Data"):
        tickers_list = [ticker.strip() for ticker in tickers_input.split(",")] if tickers_input else open("tickers.txt").read().splitlines()
        all_stock_data = pd.DataFrame()

        for ticker_symbol in tickers_list:
            try:
                stock_data = yf.download(ticker_symbol, start=start_date, end=end_date, interval='1d')
                if not stock_data.empty:
                    stock_info = yf.Ticker(ticker_symbol).info
                    stock_name = stock_info.get("shortName", ticker_symbol)
                    stock_data['Prev Open'] = stock_data['Open'].shift(1)
                    stock_data['Prev Close'] = stock_data['Close'].shift(1)
                    stock_data['Marubozu'] = stock_data.apply(is_marubozu, axis=1, threshold=marubozu_threshold)
                    stock_data['Bullish Engulfing'] = stock_data.apply(lambda row: is_bullish_engulfing(row, stock_data.loc[row.name - pd.Timedelta(days=1)]) if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1)
                    stock_data['Bearish Engulfing'] = stock_data.apply(lambda row: is_bearish_engulfing(row, stock_data.loc[row.name - pd.Timedelta(days=1)]) if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1)
                    stock_data['Bullish Harami'] = stock_data.apply(lambda row: is_bullish_harami(row, stock_data.loc[row.name - pd.Timedelta(days=1)]) if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1)
                    stock_data['Bearish Harami'] = stock_data.apply(lambda row: is_bearish_harami(row, stock_data.loc[row.name - pd.Timedelta(days=1)]) if row.name - pd.Timedelta(days=1) in stock_data.index else False, axis=1)
                    stock_data['Bearish Marubozu'] = stock_data.apply(is_bearish_marubozu, axis=1, threshold=marubozu_threshold)
                    stock_data['Opening Type'] = stock_data.apply(get_opening_type, axis=1)
                    stock_data['Stock Name'] = stock_name
                    stock_data['Avg Volume'] = stock_data['Volume'].rolling(window=10).mean()
                    stock_data['Avg Traded Price'] = (stock_data['High'] + stock_data['Low'] + stock_data['Close']) / 3
                    stock_data['Signal'] = stock_data.apply(get_signal, axis=1)
                    all_stock_data = pd.concat([all_stock_data, stock_data])
            except Exception as e:
                st.error(f"Error fetching data for {ticker_symbol}: {e}")

        if not all_stock_data.empty:
            all_stock_data['Date'] = all_stock_data.index
            all_stock_data = all_stock_data.reset_index(drop=True)

            filter_condition = pd.Series([True] * len(all_stock_data), index=all_stock_data.index)
            if patterns:
                pattern_filter_condition = pd.Series([False] * len(all_stock_data), index=all_stock_data.index)
                if 'Marubozu' in patterns:
                    pattern_filter_condition |= all_stock_data['Marubozu']
                if 'Bullish Engulfing' in patterns:
                    pattern_filter_condition |= all_stock_data['Bullish Engulfing']
                if 'Bearish Engulfing' in patterns:
                    pattern_filter_condition |= all_stock_data['Bearish Engulfing']
                if 'Bullish Harami' in patterns:
                    pattern_filter_condition |= all_stock_data['Bullish Harami']
                if 'Bearish Harami' in patterns:
                    pattern_filter_condition |= all_stock_data['Bearish Harami']
                if 'Bearish Marubozu' in patterns:
                    pattern_filter_condition |= all_stock_data['Bearish Marubozu']
                filter_condition &= pattern_filter_condition

            if signal_filter:
                filter_condition &= all_stock_data['Signal'].isin(signal_filter)

            filtered_stock_data = all_stock_data[filter_condition]

            st.markdown("<h2>Filtered Stock Data</h2>", unsafe_allow_html=True)
            st.dataframe(filtered_stock_data[['Date', 'Stock Name', 'Open', 'High', 'Low', 'Close', 'Volume', 'Avg Volume', 'Avg Traded Price', 'Marubozu', 'Bearish Marubozu', 'Bullish Engulfing', 'Bearish Engulfing', 'Bullish Harami', 'Bearish Harami', 'Signal']])

            opening_type_data = all_stock_data[['Date', 'Stock Name', 'Opening Type']]

            def color_opening_type(val):
                color = 'lightgreen' if val == "Gap Up" else 'lightcoral' if val == "Gap Down" else ''
                return f'background-color: {color}'

            st.markdown("<h2>Opening Type Data</h2>", unsafe_allow_html=True)
            st.dataframe(opening_type_data.style.applymap(color_opening_type, subset=['Opening Type']))

            summary = opening_type_data.groupby(['Stock Name', 'Opening Type']).size().reset_index(name='Count')
            st.markdown("<h2>Summary Table for Opening Types</h2>", unsafe_allow_html=True)
            st.dataframe(summary)

            def color_signal(val):
                color = 'lightgreen' if val == "Buy" else 'lightcoral' if val == "Sell" else ''
                return f'background-color: {color}'

            st.markdown("<h2>Buy and Sell Signals</h2>", unsafe_allow_html=True)
            st.dataframe(filtered_stock_data[['Date', 'Stock Name', 'Signal']].style.applymap(color_signal, subset=['Signal']))
        else:
            st.error("No data found for the given ticker symbols and date range")

    signout()
else:
    signin()

# Custom CSS for styling
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(to right, #78edcd, #4a90e2);
        }
        .css-1d391kg, .css-18e3th9 {
            background-color: #4CAF50;
        }
        .css-1d391kg input, .css-18e3th9 input {
            border-radius: 4px;
            border: 1px solid #4CAF50;
            padding: 10px;
            bacground-color: lightyellow;
        }
        .css-1d391kg button, .css-18e3th9 button {
            background-color: #4CAF50;
            color: Black;
            border-radius: 4px;
            padding: 10px;
        }
        .stButton>button:hover {
            background-color: #ffff4d;
            color: black;
            border: 2px solid #4CAF50;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 24px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            transition-duration: 0.4s;
            cursor: pointer;
        }
        .stTextInput>div>div>input {
            border: 4px solid #4CAF50;
            background-color: #ffff4d;
            color: black;
        }
    </style>
""", unsafe_allow_html=True)
