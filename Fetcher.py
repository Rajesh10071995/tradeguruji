import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
import plotly.graph_objects as go
import yfinance as yf
import plotly as pl

class NSE():
    def __init__(self, timeout=10):
        self.base_url = 'https://www.nseindia.com'
        self.session = requests.sessions.Session()
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate"
        }
        self.timeout = timeout
        self.check_connection()

    def check_connection(self):
        try:
            response = self.session.get(self.base_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to {self.base_url}: {e}")
            st.stop()

    def getHistoricalData(self, symbol, from_date, to_date, interval):
        all_data = pd.DataFrame()
        while True:
            try:
                url = f"{self.base_url}/api/historical/securityArchives?from={from_date}&to={to_date}&symbol={symbol}&dataType=priceVolumeDeliverable&series=ALL&interval={interval}"
                r = self.session.get(url, timeout=self.timeout)
                
                if r.status_code == 200:
                    data = r.json().get('data', [])
                    if not data:
                        st.warning(f"No data found for symbol {symbol} from {from_date} to {to_date}")
                        break

                    df = pd.json_normalize(data)
                    
                    # Filter only 'EQ' series
                    df = df[df['CH_SERIES'] == 'EQ']
                    
                    if df.empty:
                        st.warning(f"No 'EQ' series data found for symbol {symbol} from {from_date} to {to_date}")
                        break
                        
                    # Renaming columns to match your naming conventions
                    df = df.rename(columns={
                        '_id': 'id', 'CH_SYMBOL': 'symbol', 'CH_SERIES': 'series', 'CH_MARKET_TYPE': 'market_type',
                        'CH_TIMESTAMP': 'timestamp', 'TIMESTAMP': 'timestamp2', 'CH_TRADE_HIGH_PRICE': 'high', 
                        'CH_TRADE_LOW_PRICE': 'low', 'CH_OPENING_PRICE': 'open', 'CH_CLOSING_PRICE': 'close', 
                        'CH_LAST_TRADED_PRICE': 'ltp', 'CH_PREVIOUS_CLS_PRICE': 'prev_close', 'CH_TOT_TRADED_QTY': 'trdqty', 
                        'CH_TOT_TRADED_VAL': 'trdval', 'CH_52WEEK_HIGH_PRICE': 'hi_52_wk', 'CH_52WEEK_LOW_PRICE': 'lo_52_wk', 
                        'CH_TOTAL_TRADES': 'trades', 'CH_ISIN': 'isin', 'COP_DELIV_QTY': 'dly_qty', 
                        'COP_DELIV_PERC': 'dly_perc', 'VWAP': 'vwap', 'mTIMESTAMP': 'mtimestamp', 
                        'createdAt': 'created_at', 'updatedAt': 'updated_at'
                    })
                    
                    # Convert 'timestamp' to proper datetime format
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    df = df.dropna(subset=['timestamp'])  # Remove rows with invalid dates
                    
                    df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')
                    
                    all_data = pd.concat([all_data, df], ignore_index=True)
                    
                    # Check if the last date in the data is the same as to_date
                    if df['timestamp'].max() >= pd.to_datetime(to_date, format='%d-%m-%Y'):
                        break
                    else:
                        # Update from_date to one day after the last date in the fetched data
                        from_date = (df['timestamp'].max() + pd.Timedelta(days=1)).strftime('%d-%m-%Y')
                else:
                    st.error(f"Failed to fetch data: Status code {r.status_code}")
                    break
            except Exception as e:
                st.error(f"An error occurred: {e}")
                break
        
        # Sort the DataFrame by 'timestamp' column in descending order
        if not all_data.empty:
            all_data = all_data.sort_values(by='timestamp', ascending=False)
        
        return all_data

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bhaocopy')
        writer.close()  # Close the writer to finalize the Excel file
    processed_data = output.getvalue()
    return processed_data

def calculate_mae(df, span):
    return df.ewm(span=span, adjust=False).mean()

def generate_signals(df, short_window, long_window):
    df['MAE_short'] = calculate_mae(df['close'], short_window)
    df['MAE_long'] = calculate_mae(df['close'], long_window)
    
    # Ensure that the length matches before assignment
    signals = np.where(df['MAE_short'] > df['MAE_long'], 1, -1)
    
    df['signal'] = 0
    df.loc[df.index[short_window:], 'signal'] = signals[:len(df) - short_window]
    
    df['position'] = df['signal'].diff()
    
    # Add buy and sell signals
    df['buy_signal'] = np.where(df['position'] == 1, df['close'], np.nan)
    df['sell_signal'] = np.where(df['position'] == -1, df['close'], np.nan)
    
    return df

def plot_candlestick(df):
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlesticks'
    )])

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['buy_signal'],
        mode='markers',
        marker=dict(symbol='triangle-up', color='green', size=12),
        name='Buy Signal'
    ))

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['sell_signal'],
        mode='markers',
        marker=dict(symbol='triangle-down', color='red', size=12),
        name='Sell Signal'
    ))
    
    fig.update_layout(title='Candlestick chart with Buy and Sell Signals', xaxis_title='Date', yaxis_title='Price')
    return fig

def main():
    st.title("NSE Historical Data Fetcher")

    st.markdown("""
    ### Instructions
    1. Symbols: Enter stock symbols separated by commas (e.g., INFY, TCS, RELIANCE).
    2. Start Date: Select the start date for fetching historical data.
    3. End Date: Select the end date for fetching historical data.
    4. Select Interval: Choose the time interval for fetching data (1M, 2M, 3M, 5M, 15M, 1D, 1Month).
    5. Short EMA Window: The period for the short-term EMA.
    6. Long EMA Window: The period for the long-term EMA.
    <style>
    .markdown-text-container {
        color: green;
    }
    </style>
    """, unsafe_allow_html=True)

    uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    if uploaded_file is not None:
        symbols_df = pd.read_excel(uploaded_file)
        # Check if 'Symbol' column exists in the DataFrame
        if 'Symbol' in symbols_df.columns:
            symbols_list = symbols_df['Symbol'].tolist()
        else:
            st.error("The uploaded file does not contain a 'Symbol' column.")
            st.stop()
    else:
        symbols_list = st.sidebar.text_input("Symbols", "INFY,TCS,RELIANCE").split(',')

    start_date = st.sidebar.date_input("Start Date", datetime(2024, 1, 1))
    end_date = st.sidebar.date_input("End Date", datetime(2024, 5, 31))
    interval = st.sidebar.selectbox("Select Interval", ["1 Minute", "2 Minutes", "3 Minutes", "5 Minutes", "15 Minutes", "1 Day", "1 Month"])
    short_window = st.sidebar.number_input("Short MAE Window", min_value=1, value=12)
    long_window = st.sidebar.number_input("Long MAE Window", min_value=1, value=26)

    # Map interval selection to corresponding string
    interval_mapping = {
        "1 Minute": "1m",
        "2 Minutes": "2m",
        "3 Minutes": "3m",
        "5 Minutes": "5m",
        "15 Minutes": "15m",
        "1 Day": "1d",
        "1 Month": "1mo"
    }

    if st.sidebar.button("Fetch Data"):
        if not symbols_list:
            st.error("Please enter symbols.")
            return

        nse = NSE()
        all_data = pd.DataFrame()
        for symbol in symbols_list:
            df = nse.getHistoricalData(symbol, start_date.strftime('%d-%m-%Y'), end_date.strftime('%d-%m-%Y'), interval_mapping[interval])
            if not df.empty:
                df = generate_signals(df, short_window, long_window)
            all_data = pd.concat([all_data, df], ignore_index=True)

        if not all_data.empty:
            st.dataframe(all_data)
            st.success("Data fetched successfully.")
            excel_data = to_excel(all_data)
            st.sidebar.download_button(
                label="Download data as Excel",
                data=excel_data,
                file_name='nse_historical_data.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            # Plot candlestick chart
            fig = plot_candlestick(all_data)
            st.plotly_chart(fig)
        else:
            st.warning("No data found.")

    st.title("Stock Price Chart")

    symbol = st.text_input("Enter Stock Symbol", value="INFY")
    period = st.selectbox("Select Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"])

    if symbol:
        # Fetch data from Yahoo Finance
        data = yf.download(symbol, period=period)

        if not data.empty:
            st.subheader(f"{symbol} Stock Price Chart")
            st.line_chart(data["Close"])

            st.subheader("Candlestick Chart")
            candlestick_data = data[['Open', 'High', 'Low', 'Close']]
            st.write(candlestick_data)
            st.write('<iframe src="https://s.tradingview.com/embed-widget/candlestick/?locale=en#%7B%22symbol%22%3A%22'+symbol+'%22%2C%22width%22%3A%22800%22%2C%22height%22%3A%22320%22%2C%22interval%22%3A%22'+period+'%22%2C%22timezone%22%3A%22Etc%2FUTC%22%2C%22theme%22%3A%22light%22%2C%22style%22%3A%221%22%2C%22toolbar_bg%22%3A%22%23f1f3f6%22%2C%22enable_publishing%22%3Afalse%2C%22hide_top_toolbar%22%3Atrue%2C%22hide_legend%22%3Atrue%2C%22withdateranges%22%3Atrue%2C%22hideideas%22%3Atrue%7D" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()