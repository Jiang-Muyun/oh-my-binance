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

parser = argparse.ArgumentParser(description='sdsd')
parser.add_argument('-s', '--sym', type=str)
args = parser.parse_args()

futureClient = RequestClient(api_key=API_Key, secret_key=Secret_Key)

symbol = args.sym + 'USDT'
with open('price_record/%s.csv'%(symbol), 'a+') as fp:
    lastServerTime = 0
    while True:
        time.sleep(0.7)
        with Tick():
            marketPriceObj = futureClient.get_mark_price(symbol = symbol)
            serverTime = int(marketPriceObj.time/1000)
            if serverTime == lastServerTime:
                continue
            else:
                lastServerTime = serverTime
            
            serverTimeStr = datetime.utcfromtimestamp(serverTime).strftime("%Y-%m-%d %H:%M:%S")
            marketPrice = float(marketPriceObj.markPrice)
            text = '%s,%.6f'%(serverTimeStr, marketPrice)
            fp.write(text + '\n')
            print(text, end='')
            
