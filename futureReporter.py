import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key('account')

from utils import *
import mac_say

from binance_f import RequestClient
request_client = RequestClient(api_key=API_Key, secret_key=Secret_Key)

precision = {
    'BTC':0, 'BCH':1, 'UNI':1, 'ADA':4, 'BNB':1, 'ETH':1, 'XLM': 3, 'XRP': 3, 'DOGE': 6, 'FIL': 2, 'TRX':4,
    'LTC': 1, 'EOS': 2, 'DOT': 2, 'LINK': 1, 'ONT': 4
}
coins = {
    # 'EOS': 6.23,
    # 'LTC': 219,
    # 'LINK': 35.2,
    # 'DOGE': 0.0699,
    # 'ONT': 2.1237,
    'BTC': 40000,
    'BNB': 312,
    'ETH':2500,
    'XRP': 1.000,
    # 'BCH': 731,
    # 'UNI': 32,
    # 'ADA': 1.204,
    # 'TRX': 0.1278,
    # 'XLM': 0.572,
}

def getMarketPrices(symbolList = []):
    marketPrices = {}
    for sym in symbolList:
        marketPriceObj = request_client.get_mark_price(symbol = sym + 'USDT')
        marketPrices[sym] = float(marketPriceObj.markPrice)
    return marketPrices

def fmtPrice(price, prec=4):
    return '{:0.0{}f}'.format(price, prec)

lastReportPrice = None
reportDelta = 0.01
while True:
    print('\n\n\n\n')
    sayText = []
    marketPrices = getMarketPrices(coins.keys())

    if lastReportPrice is None:
        lastReportPrice = marketPrices
        sayText.append('Will give notifications when price change larger than %.2f%%'%(reportDelta*100))

    for sym in coins.keys():
        setPrice = coins[sym]
        marketPrice = marketPrices[sym]
        
        rate = (marketPrice - setPrice)/setPrice * 100
        rateStr = '%+.2f%%'%(rate)
        priceStr = fmtPrice(marketPrice, precision[sym])
        setPriceStr = fmtPrice(setPrice, precision[sym])
        print(underline(sym), yellow(priceStr), green(rateStr), '/', cyan(setPriceStr))
        
        if marketPrice > lastReportPrice[sym]*(1+reportDelta):
            lastReportPrice[sym] = marketPrice
            sayText.append('%s up up up %.2f%%'%(sym, reportDelta*100))
        
        elif marketPrice < lastReportPrice[sym]*(1-reportDelta):
            lastReportPrice[sym] = marketPrice
            sayText.append('%s down down down %.2f%%'%(sym, reportDelta*100))

        else:
            pass
    
    for text in sayText:
        print(yellow(text))
        macOS_Notify('Coin', text)
        os.system('afplay sounds/Hero.mp3')
        try:
            mac_say.say(text)
        except Exception as err:
            print(red(err))
    
    time.sleep(30)