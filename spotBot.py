import os
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from utils import *
from binance.client import Client
from rich.console import Console
console = Console()

def getSymbolDecimal(symbol, client=None):
    path_symbol_info = 'symbol_info/%s.json'%(symbol)
    if not os.path.exists(path_symbol_info):
        if client is None:
            raise ValueError('Must provide a Binance client to get info')
        info = client.get_symbol_info(symbol)
        with open(path_symbol_info, 'w') as fp:
            json.dump(info, fp, indent=4)
    else:
        with open(path_symbol_info, 'r') as fp:
            info = json.load(fp)
    
    for Filter in info['filters']:
        if Filter['filterType'] == 'PRICE_FILTER':
            minPrice = Filter['minPrice']
            priceDecimal = max(0, len(minPrice.split('1')[0])-1)
        if Filter['filterType'] == 'LOT_SIZE':
            minQty = Filter['minQty']
            qtyDecimal = max(0, len(minQty.split('1')[0])-1)
    return priceDecimal, qtyDecimal

class SpotBot:
    def __init__(self, X, Y, client):
        self.X = X
        self.Y = Y
        self.symbol = X+Y
        self.client = client
        self.history_order_limit = 20
        self.priceDecimal, self.qtyDecimal = getSymbolDecimal(self.symbol, self.client)

    def basic_sync(self):
        """
            for X/Y pair, get latest price, X balance and Y balance
        """
        ticker = self.client.get_ticker(symbol=self.symbol)
        self.price = float(ticker['lastPrice'])
        X_balance = self.client.get_asset_balance(asset = self.X)
        Y_balance = self.client.get_asset_balance(asset = self.Y)
        self.X_free = float(X_balance['free'])
        self.Y_free = float(Y_balance['free'])
        self.X_locked = float(X_balance['locked'])
        self.Y_locked = float(Y_balance['locked'])
        print('> %s %s, Free: %s/%s %.2f/%s'%(self.X, fmtPrice(self.price, self.priceDecimal), fmtQty(self.X_free, self.qtyDecimal), self.X, self.Y_free, self.Y))
        return self
    
    def full_sync(self):
        """
            for X/Y pair, get order history and calc gains
        """
        self.path_history = 'history/%s.csv'%(self.symbol)
        if not os.path.exists(self.path_history):
            with open(self.path_history, 'w') as fp:
                fp.write('bj_time,symbol,side,price,executedQty,clientOrderId\n')
        
        self.df = pd.read_csv(self.path_history)
        
        orders = self.client.get_all_orders(symbol=self.symbol, limit = self.history_order_limit)
        closed_orders = []
        for order in orders:
            assert order['status'] in ['NEW', 'FILLED', 'CANCELED'], order['status']

            clientOrderId = order['clientOrderId']
            if clientOrderId in self.df['clientOrderId'].values:
                continue
            
            if order['status'] in ['CANCELED', 'NEW']:
                continue
 
            bj_time = datetime.utcfromtimestamp(int(order['updateTime']/1000))+timedelta(hours=8)
            side = order['side']
            price = float(order['price'])
            executedQty = float(order['executedQty'])
            if price < 0.001:
                cummulativeQuoteQty = float(order['cummulativeQuoteQty'])
                price = cummulativeQuoteQty / executedQty
            closed_orders.append([bj_time, self.symbol, side, price, executedQty, clientOrderId])

        if len(closed_orders) > 0:
            new_df = pd.DataFrame(closed_orders)
            new_df.columns =['bj_time','symbol','side','price','executedQty','clientOrderId']
            print(new_df)
            self.df = pd.concat((self.df, new_df), ignore_index=True)
            self.df['price'] = self.df['price'].round(self.priceDecimal)
            self.df['executedQty'] = self.df['executedQty'].round(self.qtyDecimal)
            self.df.to_csv(self.path_history, index=False)
        
        self.holdingQty = 0
        self.holdingCost = 0
        self.maxHoldingCost = 0
        for index, row in self.df.iterrows():
            if row['side'] == 'BUY':
                self.holdingQty += row['executedQty']
                self.holdingCost += row['price'] * row['executedQty']
            else:
                self.holdingQty -= row['executedQty']
                self.holdingCost -= row['price'] * row['executedQty']

            if self.holdingCost > self.maxHoldingCost:
                self.maxHoldingCost = self.holdingCost
            
        if self.holdingQty < 0.0001:
            self.avgHoldingPrice = self.price
        else:
            self.avgHoldingPrice = self.holdingCost/self.holdingQty

        self.currHoldingValue = self.price * self.holdingQty
        self.currEarn = self.currHoldingValue - self.holdingCost
        return self

    def summary(self):
        # avgRate = (self.price - self.avgHoldingPrice) /self.price
        avgRate = self.currEarn / self.maxHoldingCost
        console.print('%4s/%s [yellow]%9s[/yellow] [magenta]平均成本:%9s[/magenta] |'%(
            self.X, self.Y, 
            fmtPrice(self.price, self.priceDecimal), 
            fmtPrice(self.avgHoldingPrice, self.priceDecimal)
        ), end=' ')

        console.print('%8s %4s | [yellow]收益:%6.2f[/yellow] [green]收益率:%6.2f%%[/green] | 成本/持仓价值:%6.2f / %6.2f'%(
            fmtQty(self.holdingQty, self.qtyDecimal), 
            self.X, self.currEarn, avgRate * 100, self.holdingCost, self.currHoldingValue
        ))

    def cancel_all_orders(self):
        orders = self.client.get_open_orders(symbol=self.symbol)
        cancelled = 0
        for order in orders:
            if order['status'] != 'NEW':
                continue
            try:
                self.client.cancel_order(symbol=self.symbol, orderId=order['orderId'])
                cancelled += 1
            except Exception as err:
                print('cancel_order fail', self.symbol, err)
            time.sleep(0.05)
        # if cancelled > 0:
        # print(self.symbol, 'cancelled:', cancelled)
        return cancelled

    def place_market_order(self, buy_or_sell, qty_X):
        assert buy_or_sell in ['sel', 'buy']

        qty = fmtQty(qty_X, self.qtyDecimal)

        console.print('> %s %s %s with %s'%(buy_or_sell, qty, self.X, self.Y), end=' ')
        try:
            if buy_or_sell == 'buy':
                self.client.order_market_buy(symbol=self.symbol, quantity=qty)
            else:
                self.client.order_market_sell(symbol=self.symbol, quantity=qty)

        except Exception as err:
            print(err, end=' ')
            return 0
        finally:
            print()
        
        return 1

    def place_order(self, buy_or_sell, qty_X, atPrice=None, atPercent=None):
        assert buy_or_sell in ['sel', 'buy']
        if atPrice is None:
            atPrice = self.price * atPercent

        if buy_or_sell == 'buy' and atPrice > self.price:
            print('Wrong buy order atPrice(%.4f) > price(%.4f)'%(atPrice, self.price))
            return 0

        if buy_or_sell == 'sel' and atPrice < self.price:
            print('Wrong sell order atPrice(%.4f) < price(%.4f)'%(atPrice, self.price))
            return 0

        qty_Y = atPrice * qty_X
        price = fmtPrice(atPrice, self.priceDecimal)
        qty = fmtQty(qty_X, self.qtyDecimal)

        console.print('> %s %s (%s %s / %.2f %s)'%(buy_or_sell, price, qty, self.X, qty_Y, self.Y), end=' ')
        try:
            if buy_or_sell == 'buy':
                self.client.order_limit_buy(symbol=self.symbol, quantity=qty, price=price)
            else:
                self.client.order_limit_sell(symbol=self.symbol, quantity=qty, price=price)

        except Exception as err:
            print(err, end=' ')
            return 0
        finally:
            print()
        
        return 1

if __name__ == '__main__':
    from utils import load_binance_api_key
    API_Key, Secret_Key = load_binance_api_key('account')
    coins = ['XRP', 'BCH', 'BNB', 'ETH', 'EOS', 'LTC']
    eachActionUSD = 40
    wave = 0.02

    client = Client(API_Key, Secret_Key)
    tradings = [SpotBot(coin, 'USDT', client) for coin in coins]

    while True:
        client = Client(API_Key, Secret_Key)
        for trade in tradings:
            if trade.sync(client) != 0:
                trade.cancel_all_orders()
                trade.summary()
                holdingQty, avgHoldingPrice, price = trade.holdingQty, trade.avgHoldingPrice, trade.price
                eachActionQty = eachActionUSD / price
                trade.place_order('sel', min(holdingQty, eachActionQty), atPrice=max(price, avgHoldingPrice)*(1 + wave))
                trade.place_order('buy', eachActionQty,                  atPrice=min(price, avgHoldingPrice)*(1 - wave))
                print()

        time.sleep(60)

