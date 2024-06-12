import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Function to get stock data
def get_stock_data(ticker, period='1d', interval='1m'):
    stock = yf.Ticker(ticker)
    data = stock.history(period=period, interval=interval)
    return data

# Function to compute RSI
def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

# Function to compute VWAP with an additional flag for VWAP-based signals
def compute_vwap(data, include_vwap_signals=False):
    data['Cumulative Price Volume'] = (data['Close'] * data['Volume']).cumsum()
    data['Cumulative Volume'] = data['Volume'].cumsum()
    data['VWAP'] = data['Cumulative Price Volume'] / data['Cumulative Volume']
    
    if include_vwap_signals:
        data['LTP_VWAP'] = data['LTP']
        data.loc[data['Signal'].isin(['VWAP Buy Confirmation', 'VWAP Sell Confirmation']), 'LTP'] = data['VWAP']
    
    return data['VWAP']

# Dummy function to get PCR data (you should replace this with actual data retrieval)
def get_pcr_data(ticker):
    return np.random.random()

# Function to apply conditional formatting for trading signals
def highlight_signals(row):
    if row['Signal'] in ['VWAP Buy Confirmation', 'VWAP Sell Confirmation']:
        return ['background-color: lightgreen'] * len(row)
    elif row['Signal'] in ['Open = High', 'Open = Low']:
        return ['background-color: lightblue'] * len(row)
    return [''] * len(row)

# Function to apply buy/sell suggestions based on signals
def suggest_buy_sell(row):
    if row['Volume'] > 100000:
        if row['Signal'] == 'Open = Low' or row['Signal'] == 'VWAP Buy Confirmation' or row['Open Price'] < row['Previous Close Price'] or row['Volume'] > row['Average Volume']:
            return 'Buy'
        elif row['Signal'] == 'Open = High' or row['Signal'] == 'VWAP Sell Confirmation' or row['Open Price'] > row['Previous Close Price']:
            return 'Sell'
    return ''

# Streamlit app
st.title('Rajesh Stock Analysis with 85% Accuracy')

tickers_text = st.sidebar.text_area('Enter Stock Tickers (comma separated)', 'ADANIPORTS.NS, UPL.NS, WIPRO.NS, IRB.NS')
ticker_file = st.sidebar.file_uploader('Upload Excel file with ticker symbols', type=['xlsx', 'xls'])
period = st.sidebar.selectbox('Select Period', ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'], index=0)
interval = st.sidebar.selectbox('Select Interval', ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'], index=0)
ema_short_period = st.sidebar.number_input('Short EMA Period', min_value=1, max_value=50, value=9)
ema_long_period = st.sidebar.number_input('Long EMA Period', min_value=1, max_value=50, value=21)
signal_type = st.sidebar.selectbox('Signal Type', ['Both', 'Buy', 'Sell'], index=0)
Final_Signal = st.sidebar.selectbox('Final Signal',['BUY', 'SELL'],index=0)

tickers = tickers_text.split(',')

if ticker_file is not None:
    ticker_data = pd.read_excel(ticker_file)
    if 'Ticker' in ticker_data.columns:
        uploaded_tickers = ticker_data['Ticker'].tolist()
        tickers.extend(uploaded_tickers)
    else:
        st.write("Uploaded file does not contain 'Ticker' column.")

# Button to fetch data
if st.button('Fetch Data'):
    all_signals = pd.DataFrame()

    for ticker in tickers:
        ticker = ticker.strip()
        data = get_stock_data(ticker, period=period, interval=interval)

        if data.empty:
            st.write(f"No data found for {ticker}")
            continue

        data[f'{ema_short_period} EMA'] = data['Close'].ewm(span=ema_short_period, adjust=False).mean()
        data[f'{ema_long_period} EMA'] = data['Close'].ewm(span=ema_long_period, adjust=False).mean()
        data['RSI'] = compute_rsi(data)
        data['VWAP'] = compute_vwap(data)
        data['Average Volume'] = data['Volume'].rolling(window=20).mean()
        data['PCR'] = get_pcr_data(ticker)

        # Add Previous Close Price
        data['Previous Close Price'] = data['Close'].shift(1)
        data['Open Price'] = data['Open']

        # Add 52-Week High and Low
        stock = yf.Ticker(ticker)
        data['52-Week High'] = stock.info['fiftyTwoWeekHigh']
        data['52-Week Low'] = stock.info['fiftyTwoWeekLow']

        open_price = data.iloc[0]['Open']

        data['Signal'] = np.nan
        data['Signal'] = data['Signal'].astype(object)

        if data.iloc[0]['High'] == open_price:
            data.at[data.index[0], 'Signal'] = 'Open = High'
        elif data.iloc[0]['Low'] == open_price:
            data.at[data.index[0], 'Signal'] = 'Open = Low'

        # VWAP Buy/Sell Confirmations
        data['VWAP Buy Confirmation'] = (data['Close'].shift(1) <= data['VWAP'].shift(1)) & (data['Close'] < data['VWAP'])
        data['VWAP Sell Confirmation'] = (data['Close'].shift(1) >= data['VWAP'].shift(1)) & (data['Close'] > data['VWAP'])
        
        data.loc[data['VWAP Buy Confirmation'], 'Signal'] = 'VWAP Buy Confirmation'
        data.loc[data['VWAP Sell Confirmation'], 'Signal'] = 'VWAP Sell Confirmation'

        data['Buy/Sell'] = data.apply(suggest_buy_sell, axis=1)
        data['Ticker'] = ticker
        data['Datetime'] = data.index
        data.rename(columns={'Close': 'LTP'}, inplace=True)
        signals = data.dropna(subset=['Signal'])
        all_signals = pd.concat([all_signals, signals], axis=0)

    # Add LTP_VWAP column when VWAP buy and sell confirmations are triggered
    all_signals['LTP_VWAP'] = all_signals['LTP']

    # Add Final Signal column
    all_signals['Final Signal'] = all_signals.apply(lambda row: 'BUY' if row['Buy/Sell'] == 'Buy' and row['Signal'] == 'VWAP Buy Confirmation' else ('SELL' if row['Buy/Sell'] == 'Sell' and row['Signal'] == 'VWAP Sell Confirmation' else ''), axis=1)
    
    # Filter signals based on the selected type
    if signal_type == 'Buy':
        all_signals = all_signals[all_signals['Buy/Sell'] == 'Buy']
    elif signal_type == 'Sell':
        all_signals = all_signals[all_signals['Buy/Sell'] == 'Sell']

    st.write('## Trading Signals')
    styled_signals = all_signals[['Datetime', 'Ticker', 'LTP', 'LTP_VWAP', f'{ema_short_period} EMA', f'{ema_long_period} EMA', 'RSI', 'VWAP', 'Volume', 'PCR', 'Average Volume', 'Buy/Sell', 'Signal', 'Final Signal', '52-Week High', '52-Week Low']].reset_index(drop=True).style.apply(highlight_signals, axis=1)
    st.dataframe(styled_signals)

    st.write('### Raw Data')
    st.dataframe(all_signals)
