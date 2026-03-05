import asyncio
import json

import socket
import sys
import time
import sqlite3
import numpy as np
import pandas as pd
import requests
from datetime import datetime
import bot.indicators_ta as ta
from bot.kernel import Logger
import hmac
import ccxt.async_support as ccxt
import websocket
from ccxt.base.errors import ExchangeNotAvailable

EXCHANGE = "bybit"  # kucoinfutures
MARKETS = ['BTC/USDT']
timeframes = ['1m']
SPOT = False

if EXCHANGE == 'binance':
    api_key = "5QvRaGx25ovRk5vRaCv4HZTr4BaZM33TLwDC84pOYErPrjP7WCfoSQSKWPlcmZ6k"
    api_secret = "fgafHAJYPVBNdakhQIFsBamAp326Nwl7bOJosbe6iIcn63icyKzFe20YpIU0oVlM"

if EXCHANGE == 'kucoin':
    api_key = "63e3b29210e51e0001fd7cb8"
    api_secret = "0202800f-ac6b-46bd-8fa9-fb42d13e57c3"
    password = "0120455"
    time_f = {'1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min', '1h': '1hour',
              '2h': '2hour', '4h': '4hour', '8h': '8hour', '12h': '12hour', '1d': '1day'}

if EXCHANGE == 'bybit':
    api_key = "U45jnhraOqQlo3u7uM"
    api_secret = "gEz24uSHcUrsfoFKezRfLXN8AemwPA8GD8tl"
    time_f = {'1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '2h': '120', '4h': '240',
              '6h': '360', '12h': '720', '1d': 'D'}

data_tables = ['data_' + str(timeframes[i]) for i, item in enumerate(timeframes)]

BINANCE_MARK = []
KUCOIN_MARK = []
KUCOIN_FUTURES_MARK = []
BYBIT_MARK = []

for item in MARKETS:
    BINANCE_MARK.append(item.split('/')[0] + item.split('/')[1])
for item in MARKETS:
    if SPOT == False:
        KUCOIN_MARK.append(item + ':' + item.split('/')[1])
    else:
        KUCOIN_MARK.append(item.split('/')[0] + '-' + item.split('/')[1])
for item in MARKETS:
    BYBIT_MARK.append(item.split('/')[0] + item.split('/')[1])

dict_sec = {'1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400,
            '6h': 21600, '8h': 28800, '12h': 43200, '1d': 86400}
LEVERAGE = 10

LIMIT = 200
REPLY_TIMEOUT = 5
PING_TIMEOUT = 5
SLEEP_TIME = 5



def log(*args):
    logger.info(" ".join([str(x) for x in args]))

def create_tables():
    for table in data_tables:
        create_tables_q = """
        create table if not exists
            %s (
            market TEXT,
            timestamp DATETIME,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
            );
        """ % table
        ticks_cursor.execute(create_tables_q)
        ticks_conn.commit()

def count(table, market):
    try:
        count_q = """
        SELECT
            COUNT(*)
        FROM
            '%s'
        WHERE
            market='%s'
        """ % (table, market)
        ticks_cursor.execute(count_q)
        count = ticks_cursor.fetchone()[0]
    except Exception as e:
        count = 0
    return count

async def get_ohlcv(EXCHANGE, market, interval):
    if EXCHANGE == 'bybit':
        m = market + ':' + market.split('/')[1]
    elif EXCHANGE == 'kucoinfutures':
        m = market + ':' + market.split('/')[1]
    else:
        m = market
    exchange, symbol = await configure(EXCHANGE, m)

    try:
        if EXCHANGE == 'kucoinfutures':
            now_min = int(round(time.time(), 0)) // dict_sec[interval] * dict_sec[interval]
            start_min = now_min - dict_sec[interval] * 200
            url = "https://api-futures.kucoin.com" + "/api/v1/kline/query?symbol=" + symbol + "&granularity=" + str(
                dict_sec[interval]) + "&from=" + str(start_min * 1000)
            payload = {}
            files = {}
            headers = {}
            data_df = requests.request("GET", url, headers=headers, data=payload, files=files)
            await asyncio.sleep(1.0)
            data_df = data_df.json()
            bars = data_df['data']
        else:
            bars = await exchange.fetch_ohlcv(m, interval, limit=LIMIT)
            await asyncio.sleep(1.0)

    except Exception as e:
        print('%s: %s %s' % ('ERROR', type(e).__name__, str(e)))
        return 0
        await exchange.close()
    finally:
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['volume'] = df['volume'].astype(float)
        await exchange.close()
        return df

def delete_all_from_table():
    for table in data_tables:
        ticks_cursor.execute(f"""DELETE FROM {table}""")
        ticks_conn.commit()
        print("Удалено всё по ТФ:", table.split('_')[1])

def delete_one_from_table(table, market):
    ticks_cursor.execute(f"""DELETE FROM {table} WHERE market='{market}' AND timestamp=(SELECT timestamp FROM {table} WHERE market='{market}' ORDER BY timestamp ASC LIMIT 1)""")
    ticks_conn.commit()

def insert_table(table, market, timestamp, open, high, low, close, volume):
    ticks_cursor.execute("""
         INSERT INTO %s(
             market,
             timestamp,
             open,
             high,
             low,
             close,
             volume
         ) Values (
             :market,
             :timestamp,
             :open,
             :high,
             :low,
             :close,
             :volume
         )
     """ % table, {
        'market': market,
        'timestamp': timestamp,
        'open': open,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    ticks_conn.commit()

def update_table(is_candle_closed, table, market, timestamp, open, high, low, close, volume):
    if is_candle_closed == True:
        #print("Найдена закрывающая свеча !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", table.split('_')[1])
        write_q = """
        UPDATE
            %s
        SET
            open='%s',
            high='%s',
            low='%s',
            close='%s',
            volume='%s'
        WHERE
            timestamp='%s'
            AND market='%s'
        """ % (table, open, high, low, close, volume, timestamp, market)
        ticks_cursor.execute(write_q)
        ticks_conn.commit()

    else:
        last_timestamp_q = """
        SELECT
            timestamp
        FROM
            '%s'
        WHERE
            market='%s'
        ORDER BY timestamp DESC
        LIMIT 1
        """ % (table, market)
        ticks_cursor.execute(last_timestamp_q)
        last_timestamp = ticks_cursor.fetchone()

        if last_timestamp != None:
            c = count(table, market)
            #print(c)
            if c > LIMIT:
                #print("Удалена первая свеча", table.split('_')[1], market)
                delete_one_from_table(table, market)

            if timestamp > last_timestamp[0]:  # проверка: это новая свеча или обновление?
                #print("Добавлена новая свеча", table.split('_')[1])
                insert_table(table, market, timestamp, open, high, low, close, volume)

            else:
                #print("Обновлена последняя свеча", table.split('_')[1])
                write_q = """
                UPDATE
                    %s
                SET
                    open='%s',
                    high='%s',
                    low='%s',
                    close='%s',
                    volume='%s'
                WHERE
                    timestamp='%s'
                    AND market='%s'
                """ % (table, open, high, low, close, volume, timestamp, market)
                ticks_cursor.execute(write_q)
                ticks_conn.commit()
        else:
            #print("Добавляем первые свечи", table.split('_')[1])
            insert_table(table, market, timestamp, open, high, low, close, volume)

async def configure(EXCHANGE, market):
    exchange_id = EXCHANGE
    exchange_class = getattr(ccxt, exchange_id)
    if SPOT == False:
        future = 'future'
    else:
        future = 'spot'

    if exchange_id == "kucoin" or exchange_id == "kucoinfutures":
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "password": password,
            "timeout": 30000,
            "enableRateLimit": True,
            "options": {'defaultType': future}
        })
    elif exchange_id == "bybit":
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "timeout": 30000,
            "enableRateLimit": True,
            'defaultType': future,

        })
    else:
        exchange = exchange_class({
            "apiKey": api_key,
            "secret": api_secret,
            "timeout": 30000,
            "enableRateLimit": True,
            "options": {'defaultType': future, "adjustForTimeDifference": True}
        })
    MARK = await exchange.load_markets()
    await exchange.close()
    #await exchange.load_markets()
    securities = pd.DataFrame(MARK).transpose()
    d = securities['id']
    symbol = d[market]
    return exchange, symbol

def df_get(table, market):
    df = []
    for i in range(count(table, market)):
        data_q = """
        SELECT
            timestamp,
            open,
            high,
            low,
            close,
            volume
        FROM
            %s
        WHERE
            market='%s'
        ORDER BY timestamp ASC
        """ % (table, market)
        ticks_cursor.execute(data_q)
        data = ticks_cursor.fetchall()[i]
        df.append(list(data))
    ticks_conn.commit()

    chart_data = {}
    for item in df:
        if EXCHANGE == 'binance' or EXCHANGE == 'bybit': k = 1000
        if EXCHANGE == 'kucoin' or EXCHANGE == "kucoinfutures": k = 1000
        dt_obj = (datetime.fromtimestamp(item[0]/k))
        ts = int(time.mktime(dt_obj.timetuple()))
        if not ts in chart_data:
            chart_data[ts] = {'open': float(item[1]), 'high': float(item[2]), 'low': float(item[3]), 'close': float(item[4]), 'volume': float(item[5])}
    return chart_data

def bot():
    for symbol in MARKETS:
        for tf in timeframes:
            chart_data = df_get('data_'+tf, symbol)
            opens = np.asarray([chart_data[item]['open'] for item in sorted(chart_data)])
            highs = np.asarray([chart_data[item]['high'] for item in sorted(chart_data)])
            lows = np.asarray([chart_data[item]['low'] for item in sorted(chart_data)])
            closes = np.asarray([chart_data[item]['close'] for item in sorted(chart_data)])
            volumes = np.asarray([chart_data[item]['volume'] for item in sorted(chart_data)])
            df = pd.DataFrame({'open': opens, 'close': closes, 'high': highs, 'low': lows, 'volume': volumes})

            FAST_STOCH, SLOW_STOCH = ta.STOCH(df, 14, 4, 4)
            log(symbol, 'FAST_STOCH_' + tf + '=', round(FAST_STOCH[-1], 2))
            log(symbol, 'SLOW_STOCH_' + tf + '=', round(SLOW_STOCH[-1], 2))
            log('-------------------------------')

async def fetch_ws(thread, config, logger, state, loop):
    global _state, _loop
    _state = state
    _loop = loop

    def on_message(wsapp, message):
        if EXCHANGE == 'binance':
            msg = json.loads(message)
            for tf in timeframes:
                if "kline_"+tf in msg["stream"]:
                    data = msg.get("data", {})
                    market = data.get("s")
                    candles = data.get("k")

                    if market and candles and market in BINANCE_MARK:
                        is_candle_closed = float(candles['x'])
                        t = int(candles["t"])

                        if True:
                            o = float(candles["o"])
                            h = float(candles["h"])
                            l = float(candles["l"])
                            c = float(candles["c"])
                            v = float(candles["v"])
                        for s in MARKETS:
                            if s.replace('/', '') == market:
                                update_table(is_candle_closed, 'data_'+str(tf), s, t, o, h, l, c, v)

        if EXCHANGE == 'kucoin' or EXCHANGE == "kucoinfutures":
            data = {}
            m = dict_sec
            msg = json.loads(message)
            #print(msg)
            if msg["type"] == "welcome":
                if SPOT == False:
                    for symbol in KUCOIN_FUTURES_MARK:
                        id = int(round(time.time(), 0)) * 1000
                        data = {
                        "id": id,
                        "type": "subscribe",
                        "topic": "/contract/instrument:" + symbol,
                        "response": True
                        }
                        try:
                            wsapp.send(json.dumps(data))
                        except Exception as e:
                            print('%s: %s %s' % ('ERROR', type(e).__name__, str(e)))
                else:
                    for symbol in KUCOIN_MARK:
                        for i, tf in enumerate(timeframes):
                            data[i] = {
                                "id": symbol,
                                "type": "subscribe",
                                "topic": "/market/candles:" + symbol + "_" + time_f[tf],
                                "privateChannel": False,
                                "response": True
                            }
                            try:
                                wsapp.send(json.dumps(data[i]))
                            except Exception as e:
                                print('%s: %s %s' % ('ERROR', type(e).__name__, str(e)))

            if msg["type"] == "ack":
                print("Сервер принял подписку")
                pass

            if msg["type"] == "message":
                is_candle_closed = False
                #print(msg)
                for k, symbol in enumerate(KUCOIN_MARK):
                    for i, tf in enumerate(timeframes):
                        if SPOT == False:
                            #print('Тут пытаемся получить текущую свечу')
                            now_min = int(round(time.time(), 0)) // dict_sec[tf] * dict_sec[tf]
                            start_min = now_min - dict_sec[tf] * 2
                            url = "https://api-futures.kucoin.com" + "/api/v1/kline/query?symbol=" + KUCOIN_FUTURES_MARK[k] + "&granularity=" + str(dict_sec[tf]) + "&from=" + str(start_min * 1000)
                            payload = {}
                            files = {}
                            headers = {}
                            data_df = requests.request("GET", url, headers=headers, data=payload, files=files)
                            time.sleep(0.5)
                            data_df = data_df.json()
                            bars = data_df['data']
                            t1, o1, h1, l1, c1, v1 = tuple([float(x) for x in bars[-1]])
                            t2, o2, h2, l2, c2, v2 = tuple([float(x) for x in bars[-2]])
                            update_table(is_candle_closed, 'data_' + str(tf), symbol.split(':')[0], t1, o1, h1, l1, c1, v1)
                            update_table(is_candle_closed, 'data_' + str(tf), symbol.split(':')[0], t2, o2, h2, l2, c2, v2)
                        else:
                            # now_min = int(round(time.time(), 0)) // dict_sec[tf] * dict_sec[tf]
                            # start_min = now_min - dict_sec[tf] * 2
                            # url = "https://api.kucoin.com" + "/api/v1/market/candles?type=" + str(time_f[tf]) + "&symbol=" + symbol + "&startAt=" + str(start_min)
                            # data_df = requests.request("GET", url)
                            # data_df = data_df.json()
                            # time.sleep(0.2)
                            # bars = data_df['data']
                            # t1, o1, c1, h1, l1, v1, a1 = tuple([float(x) for x in bars[0]])
                            # t2, o2, c2, h2, l2, v2, a1 = tuple([float(x) for x in bars[1]])
                            # update_table(is_candle_closed, 'data_' + str(tf), symbol.replace('-', '/'), int(t1)*1000, o1, h1, l1, c1, v1)
                            # update_table(is_candle_closed, 'data_' + str(tf), symbol.replace('-', '/'), int(t2)*1000, o2, h2, l2, c2, v2)

                            PAIRS = {symbol: {}}
                            data = msg.get("data", {})
                            symbol = data.get("symbol")
                            candles = data.get("candles")

                            if symbol and candles and symbol in PAIRS:
                                data = PAIRS[symbol]
                                candles = tuple([float(x) for x in candles])
                                kandle_start = candles[0]
                                data[kandle_start] = candles

                                if len(data) > 1:
                                    # Закрытая свеча
                                    t, o, c, h, l, v, a = data.pop(min(data, key=data.get))
                                    is_candle_closed = True
                                else:
                                    # Текущая свеча
                                    is_candle_closed = False
                                    t, o, c, h, l, v, a = tuple([float(x) for x in candles])

                            s = symbol.replace('-', '/')
                            update_table(is_candle_closed, 'data_' + str(tf), s, int(t)*1000, o, h, l, c, v)


            if msg["type"] == "ping":
                wsapp.send("""{"type": "pong", "id" "%s"}""" % msg["id"])

        if EXCHANGE == 'bybit':
            is_candle_closed = False
            msg = json.loads(message)
            #print(msg)
            for symbol in BYBIT_MARK:
                for i, tf in enumerate(timeframes):
                    if msg["topic"] and "kline."+time_f[tf]+"."+symbol in msg["topic"]:
                        data = msg.get("data", [{}])
                        candles = data[0]
                        if symbol and candles and symbol in BYBIT_MARK:
                            is_candle_closed = candles['confirm']
                            t = int(candles["start"])
                            if True:
                                o = float(candles["open"])
                                c = float(candles["close"])
                                h = float(candles["high"])
                                l = float(candles["low"])
                                v = float(candles["volume"])
                            for s in MARKETS:
                                if s.replace('/', '') == symbol:
                                    log('Updated', s)
                                    update_table(is_candle_closed, 'data_' + str(tf), s, t, o, h, l, c, v)

        bot()

    def on_error(wsapp, err):
        print("Got a an error: ", err)

    def on_open(wsapp):
        global time_f
        for symbol in BYBIT_MARK:
            for i, tf in enumerate(timeframes):
                wsapp.send("""{"op":"subscribe","args":["kline.%s.%s"]}""" % (time_f[tf], symbol))



    if EXCHANGE == 'binance':
        streams = []
        for pair in MARKETS:
            pair = pair.replace('/', '')
            for i, interval in enumerate(timeframes):
                streams.append(f"{pair.lower()}@kline_{interval}")

        print(f"Запуск сокета биржа:{EXCHANGE} потоки: {'/'.join(streams)}")

        if SPOT == False:
            url = f"wss://fstream.binance.com/stream?streams={'/'.join(streams)}"       #Для фьюч
        else:
            url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"  # Для спота

        wsapp = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error)
        wsapp.run_forever(ping_interval=3*60)


    if EXCHANGE == 'kucoin' or EXCHANGE == "kucoinfutures":
        global BASE_URL
        if SPOT == False:
            BASE_URL = "https://api-futures.kucoin.com" #Для фьюч
        else:
            BASE_URL = "https://api.kucoin.com"  # Для спота

        res = requests.post(BASE_URL + "/api/v1/bullet-public")
        token = None
        endpoint = None
        if res.status_code == requests.codes.ok:
            data = res.json().get("data", {})
            token = data.get("token")
            servers = data.get("instanceServers", [])
            if servers:
                server = servers[0]
                endpoint = server.get("endpoint", "")
                ping_interval = server.get("pingInterval", 0) / 1000
                ping_timeout = server.get("pingTimeout", 0) / 1000
        if endpoint and token:
            wsapp = websocket.WebSocketApp(f"{endpoint}?token={token}", on_message=on_message, on_error=on_error)
            wsapp.run_forever(ping_interval=ping_interval, ping_timeout=ping_timeout)

    if EXCHANGE == 'bybit':
        expires = int((time.time() + 1) * 1000)

        signature = str(hmac.new(
            bytes(api_secret, "utf-8"),
            bytes(f"GET/realtime{expires}", "utf-8"), digestmod="sha256"
        ).hexdigest())

        param = "api_key={api_key}&expires={expires}&signature={signature}".format(
            api_key=api_key,
            expires=expires,
            signature=signature
        )

        if SPOT == False:
            ws_url = "wss://stream.bybit.com/v5/public/linear" #Для фьюч
        else:
            ws_url = "wss://stream.bybit.com/v5/public/spot"  # Для спота

        url = ws_url + "?" + param
        wsapp = websocket.WebSocketApp(url, on_message=on_message, on_open=on_open, on_error=on_error)
        wsapp.run_forever(ping_interval=20)


def run(th, cfg, log, st, loop):
    global thread, config, logger, state, ticks_conn, ticks_cursor
    thread = th
    config = cfg
    logger = log
    state = st

    ticks_conn = sqlite3.connect('ticks.db', check_same_thread=False)#, check_same_thread=False
    ticks_cursor = ticks_conn.cursor()



    def log(*args):
        logger.info(" ".join([str(x) for x in args]))

    async def main(thread, config, logger, state, loop):
        global EXCHANGE, MARKETS, MARK, KUCOIN_FUTURES_MARK, LIMIT

        if EXCHANGE == 'kucoinfutures':
            for MARK in KUCOIN_MARK:
                e, s = await configure(EXCHANGE, MARK)
                KUCOIN_FUTURES_MARK.append(s)

        create_tables()

        for symbol in MARKETS:
            for i, tf in enumerate(timeframes):
                last_timestamp_q = """
                SELECT
                    timestamp
                FROM
                    '%s'
                WHERE
                    market='%s'
                ORDER BY timestamp DESC
                LIMIT 1
                """ % ('data_' + str(tf), symbol)
                ticks_cursor.execute(last_timestamp_q)
                last_timestamp = ticks_cursor.fetchone()

                now_min = int(round(time.time(), 0)) // dict_sec[tf] * dict_sec[tf]
                if last_timestamp != None and now_min * 1000 > last_timestamp[0]:
                    log('%s: %s %s' % (symbol, 'Данные свечей устарели. Нужно обновлять свечи по таймфрейму', tf))
                    delete_all_from_table()

                data_df = await get_ohlcv(EXCHANGE, symbol, tf)
                for i, item in enumerate(data_df['timestamp']):
                    t = int(data_df['timestamp'][i])
                    o = data_df['open'][i]
                    h = data_df['high'][i]
                    l = data_df['low'][i]
                    c = data_df['close'][i]
                    v = data_df['volume'][i]
                    if data_df['timestamp'][i] != 0:
                        update_table(False, 'data_' + str(tf), symbol, t, o, h, l, c, v)

        print(f"Запуск. Биржа {EXCHANGE}, Пары: {MARKETS}")
        while True:
            await fetch_ws(thread, config, logger, state, loop)

    asyncio.set_event_loop(loop)
    #loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(thread, config, logger, state, loop))
    except Exception as e:
        print('%s: %s %s' % ('ERROR', type(e).__name__, str(e)))

