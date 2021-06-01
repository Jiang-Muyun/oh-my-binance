import time
import argparse
from spotBot import SpotBot
from binance.client import Client
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key('account')

parser = argparse.ArgumentParser(description='Arbitrade in Binance USD-M Future')
parser.add_argument('-s', '--sell', action='store_true')
args = parser.parse_args()

coins = {
    'BNB' : 15.0,
    'ETH' : 10.1,
    'ADA' : 10.1,
    'DOT' : 10.1,
    'ALGO': 10.1,
    'KSM' : 10.1,
    'CAKE': 10.1,
    'MDX' : 10.1,
    # '1NCH': 10.1,
    # 'NEAR': 10.1,
    # 'IOST': 10.1,
    # 'ATOM': 10.1,
    # 'TRX' : 10.1,
}
client = Client(API_Key, Secret_Key)

for coin, USD in coins.items():
    bot = SpotBot(coin, 'USDT', client).basic_sync().full_sync()
    if args.sell:
        bot.place_market_order('sel', USD / bot.price)
    else:
        bot.place_market_order('buy', USD / bot.price)
    time.sleep(1)