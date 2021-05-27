USE AT YOUR OWN RISK
### Trade spot and future happily with binance api


### Install the python packages

```bash
pip install python-binance numpy pandas rich
```

### Install binance future api if you need to trade with USD-M Future

https://github.com/Binance-docs/Binance_Futures_python.git


### Place long or short market order several seconds ahead of a specific time and then liquidate several seconds after

- 在 2021-05-28 16:00:00 前1.5秒下一个 50 USDT 保证金的 5 倍做空 DOT的空单，然后在指定时刻后 0.5 秒平仓
```bash 
python3 future_arbitrade.py --moment "2021-05-28 16:00:00" --sym DOT --capital 50 --leverage 5 \
                            --side short --ahead 1.5 --behind 0.5
```
