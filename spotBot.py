import os
import time
import json
import pandas as pd
import numpy as np
import argparse
from decimal import Decimal
from datetime import datetime, timedelta
from binance.client import Client
from rich.console import Console
console = Console()
from utils import load_binance_api_key
API_Key, Secret_Key = load_binance_api_key

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

def fmtPrice(price, priceDecimal):
    priceFmt = '%%.%df'%(priceDecimal)
    return priceFmt%(price)

def fmtQty(qty, qtyDecimal):
    qtyFmt = '%%.%df'%(qtyDecimal)
    return qtyFmt%(qty)

class SpotBot:
    def __init__(self, X, Y, client):
        self.X = X
        self.Y = Y
        self.symbol = X+Y
        self.client = client
        self.path_history = 'history/%s.csv'%(self.symbol)
        if not os.path.exists(self.path_history):
            with open(self.path_history, 'w') as fp:
                fp.write('bj_time,symbol,side,price,executedQty,clientOrderId\n')
        self.priceDecimal, self.qtyDecimal = getSymbolDecimal(self.symbol)

    def sync(self, client=None):
        if client is not None:
            self.client = client
        self.df = pd.read_csv(self.path_history)

        ticker = self.client.get_ticker(symbol=self.symbol)
        self.lastPrice = float(ticker['lastPrice'])
        num_closed_orders = self.update_order_history()

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
            self.avgHoldingPrice = self.lastPrice
        else:
            self.avgHoldingPrice = self.holdingCost/self.holdingQty

        self.currHoldingValue = self.lastPrice * self.holdingQty
        self.currEarn = self.currHoldingValue - self.holdingCost

    def summary(self):
        # avgRate = (self.lastPrice - self.avgHoldingPrice) /self.lastPrice
        avgRate = self.currEarn / self.maxHoldingCost
        console.print('%4s/%s [yellow]%9s[/yellow] [magenta]平均成本:%9s[/magenta] |'%(
            self.X, self.Y, 
            fmtPrice(self.lastPrice, self.priceDecimal), 
            fmtPrice(self.avgHoldingPrice, self.priceDecimal)
        ), end=' ')

        console.print('%8s %4s | [yellow]收益:%6.2f[/yellow] [green]收益率:%6.2f%%[/green] | 成本/持仓价值:%6.2f / %6.2f'%(
            fmtQty(self.holdingQty, self.qtyDecimal), 
            self.X, self.currEarn, avgRate * 100, self.holdingCost, self.currHoldingValue
        ))

    def update_order_history(self):
        orders = self.client.get_all_orders(symbol=self.symbol, limit=20)
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
            console.print(new_df)
            self.df = pd.concat((self.df, new_df), ignore_index=True)
            self.df.to_csv(self.path_history, index=False)

        return len(closed_orders)

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

    def place_order(self, buy_or_sell, qty_X, atPrice=None, atPercent=None):
        assert buy_or_sell in ['sel', 'buy']
        if atPrice is None:
            atPrice = self.lastPrice * atPercent

        if buy_or_sell == 'buy' and atPrice > self.lastPrice:
            print('Wrong buy order atPrice(%.4f) > lastPrice(%.4f)'%(atPrice, self.lastPrice))
            return 0

        if buy_or_sell == 'sel' and atPrice < self.lastPrice:
            print('Wrong sell order atPrice(%.4f) < lastPrice(%.4f)'%(atPrice, self.lastPrice))
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
                holdingQty, avgHoldingPrice, lastPrice = trade.holdingQty, trade.avgHoldingPrice, trade.lastPrice
                eachActionQty = eachActionUSD / lastPrice
                trade.place_order('sel', min(holdingQty, eachActionQty), atPrice=max(lastPrice, avgHoldingPrice)*(1 + wave))
                trade.place_order('buy', eachActionQty,                  atPrice=min(lastPrice, avgHoldingPrice)*(1 - wave))
                print()

        time.sleep(60)

