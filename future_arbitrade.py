import time
import argparse
from datetime import datetime, timedelta
from utils import *
API_Key, Secret_Key = load_binance_api_key('account')

from spotBot import fmtPrice, fmtQty
from binance_f import RequestClient
from binance_f.model.constant import OrderSide, OrderType
from binance_f.base.printobject import PrintBasic, PrintMix

def assertDstTimeInFuture(dstTime):
    nowTime = time.time()
    if nowTime > dstTime:
        print('dstTime', datetime.utcfromtimestamp(dstTime).strftime("%Y-%m-%d %H:%M:%S"))
        print('nowTime', datetime.utcfromtimestamp(nowTime).strftime("%Y-%m-%d %H:%M:%S"))
        raise ValueError('Timestamp is in the past')

def waitUntill(dstTime, text=''):
    # dstStr = datetime.utcfromtimestamp(dstTime).strftime("%Y-%m-%d %H:%M:%S")
    while True:
        deltaTime = time.time() - dstTime
        nowStr = datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")
        print(text, '> %.2f | Now(UTC): %s   '%(deltaTime, nowStr), end='\r')
        if deltaTime > 0:
            print(text, 'time up!', ' '*40)
            break
        time.sleep(0.01)

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arbitrade in Binance USD-M Future')
    parser.add_argument('-s', '--sym', type=str, default='ETH')
    parser.add_argument('-c', '--capital', type=int, default=20)
    parser.add_argument('-l', '--leverage', type=int, default=20)
    parser.add_argument('-m','--moment', type=str)
    parser.add_argument('-s','--side', type=str, choices=['long', 'short'])
    parser.add_argument('-t1','--ahead', type=float, default=1.0)
    parser.add_argument('-t2','--behind', type=float, default=1.0)
    args = parser.parse_args()

    # dstTime = datetime.strptime('2021-04-17 16:00:00', '%Y-%m-%d %H:%M:%S').timestamp()
    dstTime = datetime.strptime(args.moment).timestamp()
    if args.side == 'long':
        action1, action2 = 'buy', 'sel'
        msg = '准备做多'
    else:
        action1, action2 = 'sel', 'buy'
        msg = '准备做空'

    bot = FutureBot(args.sym, args.leverage, RequestClient(api_key=API_Key, secret_key=Secret_Key))

    # Make sure the start time is in the future
    assertDstTimeInFuture(dstTime - args.ahead)

    # Wait untill the start time
    waitUntill(dstTime - args.ahead, green(msg))

    # Do action1
    bot.placeMarketOrder('sel', args.capital)

    # Wait untill the end time
    waitUntill(dstTime + args.behind, yellow('准备平仓'))

    # Do action2
    bot.placeMarketOrder('buy', args.capital)