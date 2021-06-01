import os
import time
import json
import datetime

def bold(x):       return '\033[1m'  + str(x) + '\033[0m'
def dim(x):        return '\033[2m'  + str(x) + '\033[0m'
def italicized(x): return '\033[3m'  + str(x) + '\033[0m'
def underline(x):  return '\033[4m'  + str(x) + '\033[0m'
def blink(x):      return '\033[5m'  + str(x) + '\033[0m'
def inverse(x):    return '\033[7m'  + str(x) + '\033[0m'
def gray(x):       return '\033[90m' + str(x) + '\033[0m'
def red(x):        return '\033[91m' + str(x) + '\033[0m'
def green(x):      return '\033[92m' + str(x) + '\033[0m'
def yellow(x):     return '\033[93m' + str(x) + '\033[0m'
def blue(x):       return '\033[94m' + str(x) + '\033[0m'
def magenta(x):    return '\033[95m' + str(x) + '\033[0m'
def cyan(x):       return '\033[96m' + str(x) + '\033[0m'
def white(x):      return '\033[97m' + str(x) + '\033[0m'

# ------------------------------ Timing -----------------------------------------

def macOS_Notify(title, text):
    os.system("""
              osascript -e 'display notification "{}" with title "{}"'
              """.format(text, title))

class Tick():
    def __init__(self, name='', silent=False):
        self.name = name
        self.silent = silent

    def __enter__(self):
        self.t_start = time.time()
        if not self.silent:
            print('%s ' % (self.name), end='', flush=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.t_end = time.time()
        self.delta = self.t_end-self.t_start
        self.fps = 1/self.delta

        if not self.silent:
            print(yellow('[%.3fs]' % (self.delta), ), flush=True)

class Tock():
    def __init__(self, name=None, report_time=True):
        self.name = '' if name == None else name+':'
        self.report_time = report_time

    def __enter__(self):
        self.t_start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.t_end = time.time()
        self.delta = self.t_end-self.t_start
        self.fps = 1/self.delta
        if self.report_time:
            print(yellow(self.name)+cyan('%.3fs'%(self.delta)), end=' ', flush=True)
        else:
            print(yellow('.'), end='', flush=True)

def now():
    return str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def load_binance_api_key(alias='account'):
    key_filename = 'private/%s.json'%(alias)
    if not os.path.exists(key_filename):

        raise FileNotFoundError(
            yellow('Could not find [private/account.json], Apply a api key from Binance and fill the info in [private/account.json]')
        )
    
    with open(key_filename, 'r') as fp:
        data = json.load(fp)
    return data['API_Key'], data['Secret_Key']

def fmtPrice(price, priceDecimal):
    priceFmt = '%%.%df'%(priceDecimal)
    return priceFmt%(price)

def fmtQty(qty, qtyDecimal):
    qtyFmt = '%%.%df'%(qtyDecimal)
    return qtyFmt%(qty)
