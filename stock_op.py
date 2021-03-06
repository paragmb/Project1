
"""Dual-Ticker Portfolio Assessor

This is a command line application to optimize stock portfolio.


"""
import sys
from tkinter.messagebox import NO
from turtle import title
import fire
import questionary
import os
import numpy as np
import pandas as pd
#import pandas_datareader as web
#from datetime import datetime
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from MCForecastTools import MCSimulation
from matplotlib import pyplot as plt
import hvplot.pandas
import holoviews as hv

# setting bokeh as backend
hv.extension('bokeh')

# going to use show() to open plot in browser
from bokeh.plotting import show

# Load the environment variables from the .env file
#by calling the load_dotenv function
load_dotenv()

# Set the variables for the Alpaca API and secret keys
alpaca_api_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")

# Create the Alpaca tradeapi.REST object
alpaca = tradeapi.REST(
  alpaca_api_key,
  alpaca_secret_key,
  api_version = "v2"
)

def get_investor_info():
    """Prompt dialog to get the investor's stock and initial investment information.

    Returns:
        Returns the investor's information.
    """
    print(f"Select 2 Stocks: AAL, AAPL, AMZN, F, FB, GOOGL, TSLA, TWTR")
    ticker1 = questionary.text("What's your stock1 symbol/ticker?").ask()
    ticker2 = questionary.text("What's your stock2 symbol/ticker?").ask()
    ratio1 = questionary.text("What's your ratio for stock1?").ask()
    ratio2 = questionary.text("What's your ratio for stock2?").ask()
    inves_amt = questionary.text("What's your investment amount?").ask()

    ticker1 = str(ticker1)
    ticker2 = str(ticker2)
    ratio1 = float(ratio1)
    ratio2 = float(ratio2)
    inves_amt = float(inves_amt)

    return ticker1, ticker2, ratio1, ratio2, inves_amt


def pull_stock_data(ticker1, ticker2):
    """used to grab the stock prices, with yahoo
       basis: 3 years of historical data
    """
    # SPY is added to see how the two stocks performing w.r.t. the market
    tickers = [ticker1, ticker2, "SPY"]  
    #tickers.append(ticker1) 
    #tickers.append(ticker2)

    # Set start and end dates of 3 years back from your current date(2022-01-31)
    start_date = pd.Timestamp("2019-01-31", tz="America/New_York").isoformat()
    end_date = pd.Timestamp("2022-01-31", tz="America/New_York").isoformat()
    timeframe = "1D"
    limit_rows = 1000

    # Use the Alpaca get_barset function to make the API call to get the 3 years worth of pricing data
    prices_df = alpaca.get_barset(
        tickers,
        timeframe,
        start=start_date,
        end=end_date,
        limit=limit_rows
    ).df
    print(prices_df.head())
    print(prices_df.tail())
    return prices_df
    
def quantitative_analysis(prices_df):
    
    # Analyze daily_returns
    close_prices_df = prices_df.iloc[:,[3,8,13]]
    print(close_prices_df)
    portfolio_daily_returns = close_prices_df.pct_change().dropna()
    portfolio_daily_returns.plot(title="Daily Return - Portfolio and S&P 500")
    plt.legend(title=False)
    plt.show()

    # Analyze cumulative_returns
    portfolio_cumulative_returns = (1 + portfolio_daily_returns).cumprod() - 1
    portfolio_cumulative_returns.plot(title="Cumulative Returns - Portfolio and S&P 500")
    plt.legend(title=False)
    plt.show()

    # Analyze volatility
    # Let's 1st remove the outliner to allow to zoom into the box-plot
    # Let's define a new dataframe portfolio_daily_returns_zoom
    portfolio_daily_returns_zoom = portfolio_daily_returns[portfolio_daily_returns > -0.25]
    portfolio_daily_returns_zoom.plot(kind='box', title="Daily Return - Portfolio and S&P 500")
    plt.show()

    # Analyze risk (using standard deviation; basis - rolling 21-day)
    portfolio_daily_returns_zoom.rolling(window=21).std().plot(title="Rolling 21-day Standard Deviation - Portfolio and S&P 500")
    plt.legend(title=False)
    plt.show()

    # Analyze risk-return (Sharpe Ratio)
    year_trading_days = 252
    annualized_standard_deviation = portfolio_daily_returns.std() * (year_trading_days) ** (1/2)
    average_annual_return = portfolio_daily_returns.mean() * year_trading_days
    sharpe_ratios = average_annual_return / annualized_standard_deviation
    sharpe_ratios.plot.bar(rot=0, title="Sharpe Ratios - Portfolio and S&P 500")
    plt.show()

def fin_forecast(ratio1, ratio2, prices_df, inves_amt, ticker1, ticker2):
    """used to forecast 3 years of financial forecast/projection
    """
    #print("print test line 6")
    sim_prices_df = prices_df.drop(labels=['SPY'], axis =1)
    print(sim_prices_df.head())
    print(sim_prices_df.tail())

    forecast = MCSimulation(
        portfolio_data = sim_prices_df,
        weights = [ratio1, ratio2],
        num_simulation = 500,
        num_trading_days = 252*3
    )
    print(forecast.portfolio_data.head())

    # Run the Monte Carlo simulation to forecast 3 years cumulative returns
    print(forecast.calc_cumulative_return())

    # Visualize the 3-year Monte Carlo simulation by creating an
    # overlay line plot
    forecast_line_plot = forecast.plot_simulation()
    plt.show()

    # Visualize the probability distribution of the 3-year Monte Carlo simulation 
    # by plotting a histogram

    forecast_distribution_plot = forecast.plot_distribution()
    plt.show()
    
    #Generate summary statistics from the 3-year Monte Carlo simulation results
    # Save the results as a variable; we name it as MC_retire_table
    forecast_table = forecast.summarize_cumulative_return()
    
    # Review the 3-year Monte Carlo summary statistics
    print(forecast_table)

    # Use the lower and upper `95%` confidence intervals to calculate the range of the possible outcomes for the current stock/bond portfolio
    ci_lower_cumulative_return = forecast_table[8] * (inves_amt)
    ci_upper_cumulative_return = forecast_table[9]  * (inves_amt)

    print(f"There is a 95% chance that the current stock/bond portfolio value of ${(inves_amt):.2f}"
      f" over the next 3 years will end within the range of ${ci_lower_cumulative_return:.2f} and ${ci_upper_cumulative_return:.2f}.")

    #Plotting the future value CIs
    future_data = [ci_lower_cumulative_return,ci_upper_cumulative_return]
    future_df = pd.DataFrame(data=future_data, columns=["Future Value"], index=['Future_Lower', 'Future_Upper'])
    #print(future_df)

    per_ratio1 = ratio1*100
    per_ratio2 = ratio2*100

    #print(f"For {per_ratio1} of {ticker1} and {per_ratio2} of {ticker2} at {inves_amt}")
    futureplot = future_df.hvplot.bar(y='Future Value', ylabel='Future Value($)', rot=0, color="orange",figsize=(5,5), title=f"Future Value (3 yrs) - {per_ratio1:.0f}% of {ticker1} & {per_ratio2:.0f}% of {ticker2} for ${inves_amt}")
    #plt.show()
    show(hv.render(futureplot))

    return forecast

def run():
    """The main function for running the script."""

    
    # Get the investor's information
    ticker1, ticker2, ratio1, ratio2, inves_amt = get_investor_info()

    # Used to grab the stock prices, with Alpaca
    prices_df = pull_stock_data(ticker1, ticker2)

    # Perform Quantitative Analysis
    quantitative_analysis(prices_df)
    
    # Perform Forecast Analysis
    fin_forecast(ratio1,ratio2,prices_df,inves_amt,ticker1,ticker2)
    
    
if __name__ == "__main__":
    fire.Fire(run)
