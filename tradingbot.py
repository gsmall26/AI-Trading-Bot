from lumibot.brokers import Alpaca #broker
from lumibot.backtesting import YahooDataBacktesting #framework for backtesting
from lumibot.strategies.strategy import Strategy #trading bot
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

#all generated from alpaca
API_KEY = "PKDY7WPPPW1JFHLVNBP1" 
API_SECRET = "rzsMAS4taQm8QNBfTpN5MPQ0xGKZ6wSqU5jG9Lhx"
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY" : API_KEY,
    "API_SECRET" : API_SECRET,
    "PAPER" : True
}

class MLTrader(Strategy): #inherits Strategy class 
    #life cycle methods: when we start them, initialize method runs once, on_trading_iteration runs every time we get a tick (when we get new data)
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H" #how frequently we trade
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)
    
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0) #how many units we are going to get per amount we want to risk
        return cash, last_price, quantity
        #position size calculated based on metrix cash at risk
        #higher number means more cash per trade -> 0.5 cash_at_risk = 50% of remaining cash balance

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime("%Y-%m-%d"), three_days_prior.strftime("%Y-%m-%d") #format as string, thats how API expects it

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol,
                                start=three_days_prior,
                                end=today)
        news = [ev.__dict__["_raw"]["headline"]for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        #another check
        if cash > last_price: #not buying when we don't have cash
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                #order itself
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket", #limit, market, etc
                    take_profit_price = last_price * 1.20, # profit is 20%
                    stop_loss_price = last_price * .95 #loss is 5%, depends if it is short or long order
                )
                self.submit_order(order)
                self.last_trade = "buy"
            
            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                #order itself
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket", #limit, market, etc
                    take_profit_price = last_price * .8, 
                    stop_loss_price = last_price * 1.05
                )
                self.submit_order(order)
                self.last_trade = "sell"


start_date = datetime(2020, 1, 1) #y,m,d
end_date = datetime(2023, 12, 31)

broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name="mlstrat", broker=broker, 
                 parameters={"symbol":"SPY", "cash_at_risk":.5})

strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol":"SPY", "cash_at_risk":.5}
)

#if we want to deploy this live
# trader = Trader() #connect our trader
# trader.add_strategy(strategy) #add our strategy
# trader.run_all() #run our strategy inside of our broker




#NOTES
#Dynamic position sizing means that you adjust the size of your trades
#according to the changing market conditions, such as price, volatility, trend, or indicators.

#Backtesting is evaluating the effectiveness of a trading strategy by running it against historical data