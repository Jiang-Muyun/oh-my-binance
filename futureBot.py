import time
from datetime import datetime
from utils import *
from binance_f import RequestClient
from binance_f.model.constant import OrderSide, OrderType
from binance_f.base.printobject import PrintBasic, PrintMix

class FutureBot():
    futureCoinDecimal = {
            'BTC': 3,
            'ETH': 3,
            'TRX': 0,
            'XLM': 0,
            'BNB': 2,
            'ADA': 2,
            "LTC": 3,
            'XRP': 1,
            'EOS': 1,
            'DOT': 1,
            'FIL': 1,
            'UNI': 0,
        }

    def __init__(self, sym, leverage, futureClient):
        self.sym = sym
        self.symbol = self.sym + 'USDT'
        self.futureClient = futureClient
        self.qtyDecimal = self.futureCoinDecimal[self.sym]
        self.leverage = leverage
        assert leverage <= 20, 'Too much risk'
        with Tick('Change Leverage %s -> %d'%(self.sym, self.leverage)):
            self.futureClient.change_initial_leverage(symbol = self.symbol, leverage=self.leverage)
        self.sync()

    def sync(self):
        localTime1 = time.time()
        marketPriceObj = self.futureClient.get_mark_price(symbol = self.symbol)
        localTime2 = time.time()
        serverTime = int(marketPriceObj.time/1000)
        self.marketPrice = float(marketPriceObj.markPrice)
        self.lastFundingRate = marketPriceObj.lastFundingRate
        self.nextFundingTime = int(marketPriceObj.nextFundingTime/1000)
        print(
            magenta('去程延迟 %.1fms'%((serverTime - localTime1)*100)),
            cyan('回程延迟 %.1fms'%((localTime2 - serverTime)*100)),
            green('资金费率 %.4f%%'%(self.lastFundingRate*100)),
            yellow('下次结算: %s'%(datetime.utcfromtimestamp(self.nextFundingTime).strftime("%Y-%m-%d %H:%M:%S"))),
        )

    def placeMarketOrder(self, orderSide, capital):
        assert orderSide in ['buy', 'sel']
        side = OrderSide.SELL if orderSide == 'sel' else OrderSide.BUY
        
        quantity = fmtQty(capital/self.marketPrice * self.leverage, self.qtyDecimal)

        with Tick('以市场价下 %s %s 单, 下单量 %s %s, 保证金:%s USDT'%(self.sym, orderSide, quantity, self.sym, str(capital))):
            self.futureClient.post_order(
                symbol = self.symbol, side = side, ordertype = OrderType.MARKET,quantity = quantity,positionSide = "BOTH"
            )