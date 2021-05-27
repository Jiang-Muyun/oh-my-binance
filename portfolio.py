import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from binance.client import Client
from rich.console import Console
console = Console()
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key('account')

from spotBot import SpotBot

client = Client(API_Key, Secret_Key)
coins = ['BTC', 'ETH', 'BNB']
spotCoin = [SpotBot(coin, 'USDT', client) for coin in coins]

for bot in spotCoin:
    bot.sync()
    print('Sync %s ...'%(bot.X))

print()
currEarn, holdingValue = 0, 0
for bot in spotCoin:
    currEarn += bot.currEarn
    holdingValue += bot.currHoldingValue
    if bot.currHoldingValue < 0.01:
        continue
    bot.summary()

console.print('合计收益: %.1f USDT, 持仓价值: %.1f USDT'%(currEarn, holdingValue))