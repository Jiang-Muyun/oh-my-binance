import time
import argparse
from utils import *
from datetime import datetime, timedelta
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key('account')

from spotBot import fmtPrice, fmtQty
from binance_f import RequestClient
from binance_f.model.constant import OrderSide, OrderType
from binance_f.base.printobject import PrintBasic, PrintMix

futureClient = RequestClient(api_key=API_Key, secret_key=Secret_Key)
sym = 'XRP'

while True:
    lastPrice = 0
    lastTime = time.time()
    with Tick('getMarketPrices'):
        marketPriceObj = futureClient.get_mark_price(symbol = sym + 'USDT')
        # PrintBasic.print_obj(marketPriceObj)
        marketPrice = float(marketPriceObj.markPrice)
        print(marketPrice, marketPriceObj.time, end='')
        time.sleep(0.5)