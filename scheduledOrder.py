from spotBot import SpotBot
from binance.client import Client
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key('account')

USDT_per_order = 10.02
coins = ['ETH', 'ADA', 'DOT', 'ALGO', 'KSM', 'CAKE', 'MDX']
client = Client(API_Key, Secret_Key)

for coin in coins:
    bot = SpotBot(coin, 'USDT', client).sync()
    bot.place_market_order('buy', USDT_per_order / bot.lastPrice)