import time
import argparse
from datetime import datetime
from futureBot import FutureBot
from utils import *
API_Key, Secret_Key = load_binance_api_key('account')
from binance_f import RequestClient

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