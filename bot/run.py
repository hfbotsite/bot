import asyncio
import json
import logging
import socket
import sys
import time
import re
import math
import sqlite3
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from typing import Tuple, List, Dict, Optional
import ccxt.async_support as ccxt
from bot.kernel import Connector
from ccxt.base.errors import ExchangeNotAvailable
from bot.defines import LANGUAGES
import bot.indicators_ta as ta
from decimal import Decimal
import warnings
import os

os.environ['REQUESTS_CA_BUNDLE'] = "_internal/certifi/cacert.pem"
np.seterr(all="ignore")


if sys.platform == 'win32':
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run(thread, config, logger, state, loop):
    #from uuid import getnode as get_mac
    #mac = get_mac()

    # config = Config("config.toml")
    # config.load()
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    cursor = conn.cursor()

    connector = Connector()
    start_time = time.time()


    expire_UTC = datetime.strptime("2025-02-17 00:00:00.0", '%Y-%m-%d %H:%M:%S.%f')
    LANG = config.get_value("bot", "language")

    USE_TELEGRAM = config.get_value("telegram", "use_telegram")
    telegram_api_token = config.get_value("telegram", "api_token")
    telegram_chat_id = config.get_value("telegram", "chat_id")
    only_for_fixes = config.get_value("telegram", "only_for_fixes")

    EMERGENCY_AVERAGING = config.get_value("bot", "emergency_averaging")
    if USE_TELEGRAM == True and (telegram_api_token == "" or telegram_chat_id == ""):
        USE_TELEGRAM = False
    else:
        USE_TELEGRAM = config.get_value("telegram", "use_telegram")

    EXCHANGE = config.get_value("bot", "exchange")

    MARKETS = []

    BASE_COIN = config.get_value("bot", "base_coin")
    QUOTE_COIN = config.get_value("bot", "quote_coin")
    base_coins = BASE_COIN.replace(' ', '').split(',')
    MY_NOTE = config.get_value("bot", "my_note")

    for i in base_coins:
        MARKETS.append(str(i) + "/" + str(QUOTE_COIN))

    USE_WHITELIST = config.get_value("whitelist", "use_whitelist")
    #MARKET = config.get_value("bot", "market")


    #LEVERAGE_ARRAY = LEVERAGES.replace(' ', '').split(',')

    PERCENT_OR_AMOUNT = config.get_value("bot", "percent_or_amount")
    ACTIVE_ORDERS = config.get_value("bot", "active_orders")

    STEP_ONE = config.get_value("bot", "first_step")
    if STEP_ONE == 0 and (EXCHANGE == 'gateio' or EXCHANGE == "coinex"):
        STEP_ONE = 0.01

    STOP_IF_NO_BALANCE = config.get_value("bot", "stop_if_no_balance")
    if STOP_IF_NO_BALANCE == None:
        STOP_IF_NO_BALANCE = True

    OVERLAP_PRICE = config.get_value("bot", "range_cover")

    FIRST_CO_KOEFF = config.get_value("bot", "first_so_coeff")
    DYNAMIC_CO_KOEFF = config.get_value("bot", "dynamic_so_coeff")

    LIFT_STEP = config.get_value("bot", "lift_step")
    USE_MARGIN = config.get_value("bot", "use_margin")
    MARGIN_TOP = config.get_value("bot", "margin_top")
    MARGIN_BOTTOM = config.get_value("bot", "margin_bottom")
    CANCEL_ON_TREND = config.get_value("bot", "cancel_on_trend")

    SQUEEZE_PROFIT = config.get_value("exit", "squeeze_profit")
    TRAILING_STOP = config.get_value("exit", "trailing_stop")
    LIMIT_STOP = config.get_value("exit", "limit_stop")

    BACK_PROFIT = config.get_value("bot", "back_profit")

    MARTINGALE = config.get_value("bot", "martingale")

    #USE_DYNAMIC_CO = config.get_value("averaging", "use_dynamic_so")
    all_timeframes = config.get_value("averaging", "timeframe").replace(' ', '').split(',')

    GLOBAL_TF = config.get_value("indicators_tuning", "global_timeframe")
    NEW_ORDER_TIME = config.get_value("bot", "new_order_time")
    CO_SAFETY_PRICE = config.get_value("bot", "so_safety_price")

    if ACTIVE_ORDERS == 0:
        imm = 1
    else:
        imm = 0


    USE_STOCH_RSI = config.get_value("indicators_tuning", "use_stoch_rsi")
    if USE_STOCH_RSI == True:
        text_stoch = 'STOCHRSI'
    else:
        text_stoch = 'STOCH'
    EMA200_LENGTH = config.get_value("indicators_tuning", "ema200_length")
    EMA200_DELTA = config.get_value("indicators_tuning", "ema200_delta")
    USE_GLOBAL_STOCH = config.get_value("indicators_tuning", "use_global_stoch")
    GLOBAL_STOCH_LONG_UP_LEVEL = config.get_value("indicators_tuning", "global_stoch_long_up_level")
    GLOBAL_STOCH_LONG_LOW_LEVEL = config.get_value("indicators_tuning", "global_stoch_long_low_level")
    GLOBAL_STOCH_SHORT_UP_LEVEL = config.get_value("indicators_tuning", "global_stoch_short_up_level")
    GLOBAL_STOCH_SHORT_LOW_LEVEL = config.get_value("indicators_tuning", "global_stoch_short_low_level")
    FASTK_PERIOD = config.get_value("indicators_tuning", "stoch_fastk_period")
    SLOWK_PERIOD = config.get_value("indicators_tuning", "stoch_slowk_period")
    SLOWD_PERIOD = config.get_value("indicators_tuning", "stoch_slowd_period")
    CCI_LENGTH = config.get_value("indicators_tuning", "cci_length")
    RSI_LENGTH = config.get_value("indicators_tuning", "rsi_length")
    RSI_SMA_LENGTH = config.get_value("indicators_tuning", "rsi_sma_length")
    MACD_F = config.get_value("indicators_tuning", "macd_f")
    MACD_S = config.get_value("indicators_tuning", "macd_s")
    MACD_SIGNAL = config.get_value("indicators_tuning", "macd_signal")
    BB_PERIOD = config.get_value("indicators_tuning", "bb_period")
    BB_DEV = config.get_value("indicators_tuning", "bb_dev")
    ATR_LENGTH = config.get_value("indicators_tuning", "atr_length")
    EFI_LENGTH = config.get_value("indicators_tuning", "efi_length")
    EXTREMES_LEFT = config.get_value("indicators_tuning", "extremes_left")
    EXTREMES_RIGHT = config.get_value("indicators_tuning", "extremes_right")

    ENTRY_PRESET = config.get_value("entry", "entry_preset")
    AVG_PRESET = config.get_value("averaging", "avg_preset")
    EXIT_PRESET = config.get_value("exit", "exit_preset")

    # STOCH_CCI
    ENTRY_USE_STOCH_C = config.get_value("entry_preset_stoch_cci", "use_stoch")
    ENTRY_USE_CCI = config.get_value("entry_preset_stoch_cci", "use_cci")
    ENTRY_BASIC_INDICATOR_C = config.get_value("entry_preset_stoch_cci", "basic_indicator")
    ENTRY_STOCH_C_LONG_UP_LEVEL = config.get_value("entry_preset_stoch_cci", "stoch_long_up_level")
    ENTRY_STOCH_C_LONG_LOW_LEVEL = config.get_value("entry_preset_stoch_cci", "stoch_long_low_level")
    ENTRY_CCI_LONG_LEVEL = config.get_value("entry_preset_stoch_cci", "cci_long_level")
    ENTRY_STOCH_C_SHORT_UP_LEVEL = config.get_value("entry_preset_stoch_cci", "stoch_short_up_level")
    ENTRY_STOCH_C_SHORT_LOW_LEVEL = config.get_value("entry_preset_stoch_cci", "stoch_short_low_level")
    ENTRY_CCI_SHORT_LEVEL = config.get_value("entry_preset_stoch_cci", "cci_short_level")

    AVG_USE_STOCH_C = config.get_value("avg_preset_stoch_cci", "use_stoch")
    AVG_USE_CCI = config.get_value("avg_preset_stoch_cci", "use_cci")
    AVG_BASIC_INDICATOR_C = config.get_value("avg_preset_stoch_cci", "basic_indicator")
    AVG_STOCH_C_LONG_UP_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_long_up_level")
    AVG_STOCH_C_LONG_LOW_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_long_low_level")
    AVG_CCI_LONG_LEVEL = config.get_value("avg_preset_stoch_cci", "cci_long_level")
    AVG_STOCH_C_SHORT_UP_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_short_up_level")
    AVG_STOCH_C_SHORT_LOW_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_short_low_level")
    AVG_CCI_SHORT_LEVEL = config.get_value("avg_preset_stoch_cci", "cci_short_level")

    EXIT_USE_STOCH_C = config.get_value("exit_preset_stoch_cci", "use_stoch")
    EXIT_USE_CCI = config.get_value("exit_preset_stoch_cci", "use_cci")
    EXIT_BASIC_INDICATOR_C = config.get_value("exit_preset_stoch_cci", "basic_indicator")
    EXIT_STOCH_C_LONG_UP_LEVEL = config.get_value("exit_preset_stoch_cci", "stoch_long_up_level")
    EXIT_STOCH_C_LONG_LOW_LEVEL = config.get_value("exit_preset_stoch_cci", "stoch_long_low_level")
    EXIT_CCI_LONG_LEVEL = config.get_value("exit_preset_stoch_cci", "cci_long_level")
    EXIT_STOCH_C_SHORT_UP_LEVEL = config.get_value("exit_preset_stoch_cci", "stoch_short_up_level")
    EXIT_STOCH_C_SHORT_LOW_LEVEL = config.get_value("exit_preset_stoch_cci", "stoch_short_low_level")
    EXIT_CCI_SHORT_LEVEL = config.get_value("exit_preset_stoch_cci", "cci_short_level")

    # STOCH_RSI
    ENTRY_USE_STOCH_S = config.get_value("entry_preset_stoch_rsi", "use_stoch")
    ENTRY_USE_RSI = config.get_value("entry_preset_stoch_rsi", "use_rsi")
    ENTRY_BASIC_INDICATOR_S = config.get_value("entry_preset_stoch_rsi", "basic_indicator")
    ENTRY_STOCH_S_LONG_UP_LEVEL = config.get_value("entry_preset_stoch_rsi", "stoch_long_up_level")
    ENTRY_STOCH_S_LONG_LOW_LEVEL = config.get_value("entry_preset_stoch_rsi", "stoch_long_low_level")
    ENTRY_RSI_LONG_LEVEL = config.get_value("entry_preset_stoch_rsi", "rsi_long_level")
    ENTRY_STOCH_S_SHORT_UP_LEVEL = config.get_value("entry_preset_stoch_rsi", "stoch_short_up_level")
    ENTRY_STOCH_S_SHORT_LOW_LEVEL = config.get_value("entry_preset_stoch_rsi", "stoch_short_low_level")
    ENTRY_RSI_SHORT_LEVEL = config.get_value("entry_preset_stoch_rsi", "rsi_short_level")

    AVG_USE_STOCH_S = config.get_value("avg_preset_stoch_rsi", "use_stoch")
    AVG_USE_RSI = config.get_value("avg_preset_stoch_rsi", "use_rsi")
    AVG_BASIC_INDICATOR_S = config.get_value("avg_preset_stoch_rsi", "basic_indicator")
    AVG_STOCH_S_LONG_UP_LEVEL = config.get_value("avg_preset_stoch_rsi", "stoch_long_up_level")
    AVG_STOCH_S_LONG_LOW_LEVEL = config.get_value("avg_preset_stoch_rsi", "stoch_long_low_level")
    AVG_RSI_LONG_LEVEL = config.get_value("avg_preset_stoch_rsi", "rsi_long_level")
    AVG_STOCH_S_SHORT_UP_LEVEL = config.get_value("avg_preset_stoch_rsi", "stoch_short_up_level")
    AVG_STOCH_S_SHORT_LOW_LEVEL = config.get_value("avg_preset_stoch_rsi", "stoch_short_low_level")
    AVG_RSI_SHORT_LEVEL = config.get_value("avg_preset_stoch_rsi", "rsi_short_level")

    EXIT_USE_STOCH_S = config.get_value("exit_preset_stoch_rsi", "use_stoch")
    EXIT_USE_RSI = config.get_value("exit_preset_stoch_rsi", "use_rsi")
    EXIT_BASIC_INDICATOR_S = config.get_value("exit_preset_stoch_rsi", "basic_indicator")
    EXIT_STOCH_S_LONG_UP_LEVEL = config.get_value("exit_preset_stoch_rsi", "stoch_long_up_level")
    EXIT_STOCH_S_LONG_LOW_LEVEL = config.get_value("exit_preset_stoch_rsi", "stoch_long_low_level")
    EXIT_RSI_LONG_LEVEL = config.get_value("exit_preset_stoch_rsi", "rsi_long_level")
    EXIT_STOCH_S_SHORT_UP_LEVEL = config.get_value("exit_preset_stoch_rsi", "stoch_short_up_level")
    EXIT_STOCH_S_SHORT_LOW_LEVEL = config.get_value("exit_preset_stoch_rsi", "stoch_short_low_level")
    EXIT_RSI_SHORT_LEVEL = config.get_value("exit_preset_stoch_rsi", "rsi_short_level")

    # CCI_CROSS
    ENTRY_CCI_CROSS_LONG_LEVEL = config.get_value("entry_preset_cci_cross", "cci_long_level")
    AVG_CCI_CROSS_LONG_LEVEL = config.get_value("avg_preset_cci_cross", "cci_long_level")
    EXIT_CCI_CROSS_LONG_LEVEL = config.get_value("exit_preset_cci_cross", "cci_long_level")

    ENTRY_CCI_CROSS_SHORT_LEVEL = config.get_value("entry_preset_cci_cross", "cci_short_level")
    AVG_CCI_CROSS_SHORT_LEVEL = config.get_value("avg_preset_cci_cross", "cci_short_level")
    EXIT_CCI_CROSS_SHORT_LEVEL = config.get_value("exit_preset_cci_cross", "cci_short_level")

    ENTRY_CCI_CROSS_USE_PRICE = config.get_value("entry_preset_cci_cross", "use_price")
    AVG_CCI_CROSS_USE_PRICE = config.get_value("avg_preset_cci_cross", "use_price")
    EXIT_CCI_CROSS_USE_PRICE = config.get_value("exit_preset_cci_cross", "use_price")

    ENTRY_CCI_CROSS_METHOD = config.get_value("entry_preset_cci_cross", "cross_method")
    AVG_CCI_CROSS_METHOD = config.get_value("avg_preset_cci_cross", "cross_method")
    EXIT_CCI_CROSS_METHOD = config.get_value("exit_preset_cci_cross", "cross_method")

    # SMA_CROSS
    ENTRY_MA_CROSS_MA1 = config.get_value("entry_preset_ma_cross", "ma1_length")
    ENTRY_MA_CROSS_MA2 = config.get_value("entry_preset_ma_cross", "ma2_length")
    AVG_MA_CROSS_MA1 = config.get_value("avg_preset_ma_cross", "ma1_length")
    AVG_MA_CROSS_MA2 = config.get_value("avg_preset_ma_cross", "ma2_length")
    EXIT_MA_CROSS_MA1 = config.get_value("exit_preset_ma_cross", "ma1_length")
    EXIT_MA_CROSS_MA2 = config.get_value("exit_preset_ma_cross", "ma2_length")

    ENTRY_MA_CROSS_METHOD = config.get_value("entry_preset_ma_cross", "cross_method")
    AVG_MA_CROSS_METHOD = config.get_value("avg_preset_ma_cross", "cross_method")
    EXIT_MA_CROSS_METHOD = config.get_value("exit_preset_ma_cross", "cross_method")

    # RSI_SMARSI_CROSS
    ENTRY_SMARSI_CROSS_LONG_UP_LEVEL = config.get_value("entry_preset_rsi_smarsi_cross", "rsi_long_up_level")
    ENTRY_SMARSI_CROSS_LONG_LOW_LEVEL = config.get_value("entry_preset_rsi_smarsi_cross", "rsi_long_low_level")
    ENTRY_SMARSI_CROSS_SHORT_UP_LEVEL = config.get_value("entry_preset_rsi_smarsi_cross", "rsi_short_low_level")
    ENTRY_SMARSI_CROSS_SHORT_LOW_LEVEL = config.get_value("entry_preset_rsi_smarsi_cross", "rsi_short_low_level")
    ENTRY_SMARSI_LENGTH = config.get_value("entry_preset_rsi_smarsi_cross", "smarsi_length")

    AVG_SMARSI_CROSS_LONG_UP_LEVEL = config.get_value("avg_preset_rsi_smarsi_cross", "rsi_long_up_level")
    AVG_SMARSI_CROSS_LONG_LOW_LEVEL = config.get_value("avg_preset_rsi_smarsi_cross", "rsi_long_low_level")
    AVG_SMARSI_CROSS_SHORT_UP_LEVEL = config.get_value("avg_preset_rsi_smarsi_cross", "rsi_short_low_level")
    AVG_SMARSI_CROSS_SHORT_LOW_LEVEL = config.get_value("avg_preset_rsi_smarsi_cross", "rsi_short_low_level")
    AVG_SMARSI_LENGTH = config.get_value("avg_preset_rsi_smarsi_cross", "smarsi_length")

    EXIT_SMARSI_CROSS_LONG_UP_LEVEL = config.get_value("exit_preset_rsi_smarsi_cross", "rsi_long_up_level")
    EXIT_SMARSI_CROSS_LONG_LOW_LEVEL = config.get_value("exit_preset_rsi_smarsi_cross", "rsi_long_low_level")
    EXIT_SMARSI_CROSS_SHORT_UP_LEVEL = config.get_value("exit_preset_rsi_smarsi_cross", "rsi_short_low_level")
    EXIT_SMARSI_CROSS_SHORT_LOW_LEVEL = config.get_value("exit_preset_rsi_smarsi_cross", "rsi_short_low_level")
    EXIT_SMARSI_LENGTH = config.get_value("exit_preset_rsi_smarsi_cross", "smarsi_length")

    ENTRY_BY_INDICATORS = config.get_value("entry", "entry_by_indicators")
    ENTRY_USE_TV_SIGNALS = config.get_value("entry", "entry_use_tv_signals")
    USE_ENTRY_MARGIN = config.get_value("entry", "entry_use_entry_margin")
    ENTRY_MARGIN_TOP = config.get_value("entry", "entry_margin_top")
    ENTRY_MARGIN_BOTTOM = config.get_value("entry", "entry_margin_bottom")




    EXIT_METHOD = config.get_value("exit", "take_profit")
    EXIT_USE_TV_SIGNALS = config.get_value("exit", "exit_use_tv_signals")
    EXIT_PROFIT_LEVEL = config.get_value("exit", "exit_profit_level")
    EXIT_STOP_LOSS_LEVEL = config.get_value("exit", "exit_stop_loss_level")

    # EXIT_USE_EFI = config.get_value("exit", "exit_use_efi")
    # EXIT_EFI_SHORT_LEVEL = config.get_value("exit", "exit_efi_short_level")
    # EXIT_EFI_LONG_LEVEL = config.get_value("exit", "exit_efi_long_level")

    TIMEFRAME_SWITCHING = config.get_value("timeframe_switching", "timeframe_switching")
    EMA_GLOBAL_SWITCH = config.get_value("timeframe_switching", "ema_global_switch")
    ORDERS_SWITCH = config.get_value("timeframe_switching", "orders_switch")
    ORDERS_COUNT = config.get_value("timeframe_switching", "orders_count")
    LAST_CANDLE_SWITCH = config.get_value("timeframe_switching", "last_candle_switch")
    LAST_CANDLE_COUNT = config.get_value("timeframe_switching", "last_candle_count")
    LAST_CANDLE_ORDERS = config.get_value("timeframe_switching", "last_candle_orders")
    STOCH_ADJUSTMENT = config.get_value("timeframe_switching", "stoch_adjustment")

    ENTRY_PRICE_DELTA_SHORT = config.get_value("entry_preset_price", "price_delta_short")
    ENTRY_PRICE_DELTA_LONG = config.get_value("entry_preset_price", "price_delta_long")
    AVG_PRICE_DELTA_SHORT = config.get_value("avg_preset_price", "price_delta_short")
    AVG_PRICE_DELTA_LONG = config.get_value("avg_preset_price", "price_delta_long")

    AVG_TIMESLEEP = config.get_value("averaging", "avg_timesleep")

    # ENTRY_N = config.get_value("entry_preset_midas", "N")
    # ENTRY_M = config.get_value("entry_preset_midas", "M")
    # AVG_N = config.get_value("avg_preset_midas", "N")
    # AVG_M = config.get_value("avg_preset_midas", "M")
    # EXIT_N = config.get_value("exit_preset_midas", "M")
    # EXIT_M = config.get_value("exit_preset_midas", "M")
    # ENTRY_HLC3 = config.get_value("entry_preset_midas", "hlc3")
    # AVG_HLC3 = config.get_value("avg_preset_midas", "hlc3")
    # EXIT_HLC3 = config.get_value("exit_preset_midas", "hlc3")
    # ENTRY_H_L_PERCENT = config.get_value("entry_preset_midas", "h_l_percent")
    # AVG_H_L_PERCENT = config.get_value("avg_preset_midas", "h_l_percent")
    # EXIT_H_L_PERCENT = config.get_value("exit_preset_midas", "h_l_percent")
    #ENTRY_QFL_CROSS_METHOD = config.get_value("entry_preset_midas", "cross_method")
    #AVG_QFL_CROSS_METHOD = config.get_value("avg_preset_midas", "cross_method")
    #EXIT_QFL_CROSS_METHOD = config.get_value("exit_preset_midas", "cross_method")

    sell_remaining = False

    if ENTRY_USE_TV_SIGNALS == True or EXIT_USE_TV_SIGNALS == True:
        EMAIL = config.get_value("mail", "email")
        APP_PASSWORD = config.get_value("mail", "app_password")
        IMAP_SERVER = config.get_value("mail", "imap_server")
        IMAP_PORT = config.get_value("mail", "imap_port")

    def send_msg(text):
        url_req = "https://api.telegram.org/bot" + telegram_api_token + "/sendMessage" + "?chat_id=" + telegram_chat_id + "&text=" + text + "&parse_mode=HTML"
        results = requests.get(url_req)

    def utc_to_local_timezone(timestamp):
        now = time.time()
        utc_offset = (datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)).total_seconds()
        return timestamp + utc_offset

    def count(cur, table, market):
        count_q = """
        SELECT
            COUNT(*)
        FROM
            '%s'
        WHERE
            market='%s'
        """ % (table, market)

        cursor.execute(count_q)
        result = cursor.fetchone()
        conn.commit()
        return result

    async def fetch_ohlcv_data(server_url, exchange, pair, timeframe, api_key):
        headers = {
            "x-api-key": api_key
        }
        params = {
            "exchange": exchange,
            "pairs": ",".join(pair),
            "timeframes": ",".join(timeframe)
        }
        response = requests.get(f"{server_url}/ohlcv/data", headers=headers, params=params)
        if response.status_code == 200:
            ohlcv_data = response.json()
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp', ascending=True)
            df = df.reset_index(drop=True)
            return df
        else:
            return f"Ошибка: {response.status_code}"

    async def fetch_ind_data(server_url, exchange, pair, timeframe, api_key):
        headers = {
            "x-api-key": api_key
        }
        params = {
            "exchange": exchange,
            "pairs": pair,
            "timeframes": timeframe
        }
        response = requests.get(f"{server_url}/indicators/data", headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return f"Ошибка: {response.status_code}"

    def find_extremes(df: pd.DataFrame, current_price: float, candles) -> Dict[str, List[Dict[str, any]]]:
        min_extremes = []
        max_extremes = []

        for index in range(len(df)):
            low = df.iloc[index]['low']
            high = df.iloc[index]['high']
            timestamp = df.iloc[index]['timestamp']

            # Проверяем, что индекс + candles[1] не выходит за пределы допустимых значений
            end_index = min(index + candles[1], len(df) - 1)
            # Аналогично, убедимся, что индекс - candles[0] больше или равен 0
            start_index = max(index - candles[0], 0)

            if all(low < df.iloc[j]['low'] for j in range(max(0, start_index), min(end_index + 1, len(df))) if
                   j != index) and low < current_price:
                min_extremes.append({'timestamp': timestamp, 'price': low})

            if all(high > df.iloc[j]['high'] for j in range(max(0, start_index), min(end_index + 1, len(df))) if
                   j != index) and high > current_price:
                max_extremes.append({'timestamp': timestamp, 'price': high})

        return {'min_extremes': min_extremes, 'max_extremes': max_extremes}

    def calculate_extremes(min_extremes: List[Dict[str, float]], max_extremes: List[Dict[str, float]], leverage, current_price, timeframe):
        if timeframe in ['3m', '1m']:
            loss_range = (0.01, 0.15)  # Допустимый диапазон убытка
        elif timeframe == '5m':
            loss_range = (0.03, 0.20)
        elif timeframe == '15m':
            loss_range = (0.04, 0.25)
        elif timeframe == '30m':
            loss_range = (0.05, 0.35)
        elif timeframe == '1h':
            loss_range = (0.06, 0.40)
        elif timeframe == '2h':
            loss_range = (0.07, 0.45)
        elif timeframe == '4h':
            loss_range = (0.08, 0.55)
        elif timeframe == '8h':
            loss_range = (0.08, 0.65)
        elif timeframe == '12h':
            loss_range = (0.08, 0.70)
        elif timeframe == '1d':
            loss_range = (0.10, 0.75)
        else:
            loss_range = (0.04, 0.25)
        fixed_loss_percentage = 0.25  # Фиксированный процент убытка

        valid_min_price = []
        valid_max_price = []

        # Сортировка минимумов по времени в обратном порядке, чтобы начать с ближайшего к текущему времени
        sorted_min_extremes = sorted(min_extremes, key=lambda x: x['timestamp'], reverse=True)

        for minimum in sorted_min_extremes:
            min_price = minimum['price']
            loss = (current_price - min_price) / current_price  # Расчет потенциального убытка в долях
            # Проверяем, находится ли убыток в допустимом диапазоне
            if loss_range[0] <= loss * leverage <= loss_range[1]:
                valid_min_price.append(min_price)  # Добавляем в список валидных стоп-лоссов
        if valid_min_price:
            min_extreme = min(valid_min_price)
        else:
            min_extreme = current_price - (fixed_loss_percentage / leverage * current_price)

        sorted_max_extremes = sorted(max_extremes, key=lambda x: x['timestamp'], reverse=True)
        for maximum in sorted_max_extremes:
            max_price = maximum['price']
            loss = (max_price - current_price) / current_price
            if loss_range[0] <= loss * leverage <= loss_range[1]:
                valid_max_price.append(max_price)
        if valid_max_price:
            max_extreme = max(valid_max_price)
        else:
            max_extreme = current_price + (fixed_loss_percentage / leverage * current_price)

        return min_extreme, max_extreme

    def calculate_ind(market, df, timeframe, reason):
        #opens = np.asarray(df['open'].values)
        closes = np.asarray(df['close'].values)
        highs = np.asarray(df['high'].values)
        lows = np.asarray(df['low'].values)
        volumes = np.asarray(df['volume'].values)

        # Вычисляем все необходимые индикаторы
        ema200 = ta.EMA(closes, EMA200_LENGTH)
        # rint(timeframe,ema200[-1])
        if closes[-1] > ema200[-1] and closes[-4] > ema200[-4]:
            trend = 'LONG'
        else:
            trend = 'SHORT'

        macd, macd_signal, macd_hist = ta.MACD(closes, MACD_F, MACD_S, MACD_SIGNAL)
        stoch_fast, stoch_slow = ta.STOCH(df, FASTK_PERIOD, SLOWK_PERIOD, SLOWD_PERIOD)
        # logger.debug(f'{symbol} {stoch_fast[-1]} {stoch_slow[-1]}')
        rsi = ta.RSI(closes, RSI_LENGTH)

        cci = ta.CCI(highs, lows, closes, CCI_LENGTH)
        atr = ta.ATR(highs, lows, closes, ATR_LENGTH)
        efi = ta.EFI(df, EFI_LENGTH)

        sma_rsi = ta.SMA(rsi, RSI_SMA_LENGTH)


        if reason == "entry":
            MA_CROSS_MA1 = ENTRY_MA_CROSS_MA1
            MA_CROSS_MA2 = ENTRY_MA_CROSS_MA2
        elif reason == "avg":
            MA_CROSS_MA1 = AVG_MA_CROSS_MA1
            MA_CROSS_MA2 = AVG_MA_CROSS_MA2
        elif reason == "exit":
            MA_CROSS_MA1 = EXIT_MA_CROSS_MA1
            MA_CROSS_MA2 = EXIT_MA_CROSS_MA2
        else:
            MA_CROSS_MA1 = AVG_MA_CROSS_MA1
            MA_CROSS_MA2 = AVG_MA_CROSS_MA2


        ma_fast = ta.MA(closes, MA_CROSS_MA1)
        ma_slow = ta.MA(closes, MA_CROSS_MA2)
        bb_upper, bb_middle, bb_lower = ta.BBANDS(closes, BB_PERIOD, BB_DEV)

        extremes = find_extremes(df, closes[-1], [EXTREMES_LEFT, EXTREMES_RIGHT])
        min_extremes = extremes['min_extremes']
        max_extremes = extremes['max_extremes']

        extreme_min, extreme_max = calculate_extremes(min_extremes, max_extremes, 10, closes[-1], timeframe)

        cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % market)
        precisions = cursor.fetchall()[0]
        ap, pp, al = precisions

        ind = {
            'trend': trend,
            'ema200': round(ema200[-1], pp),
            'macd': round(macd[-1], 8),
            'macd_signal': round(macd_signal[-1], 8),
            'macd_h_1': round(macd_hist[-1], 8),
            'macd_h_2': round(macd_hist[-2], 8),
            'macd_h_3': round(macd_hist[-3], 8),
            'macd_h_4': round(macd_hist[-4], 8),
            'rsi_1': round(rsi[-1], 3),
            'rsi_2': round(rsi[-2], 3),
            'rsi_3': round(rsi[-3], 3),
            'smarsi': round(sma_rsi[-1], 3),
            'fast': round(stoch_fast[-1], 3),
            'slow': round(stoch_slow[-1], 3),
            'atr': round(atr[-1], pp),
            'efi': round(efi[-1], pp),
            'upper': round(bb_upper[-1], pp),
            'middle': round(bb_middle[-1], pp),
            'lower': round(bb_lower[-1], pp),
            'cci_1': round(cci[-1], 3),
            'cci_2': round(cci[-2], 3),
            'cci_3': round(cci[-3], 3),
            'ma_1_1': round(ma_fast[-1], pp),
            'ma_2_1': round(ma_slow[-1], pp),
            'ma_1_2': round(ma_fast[-2], pp),
            'ma_2_2': round(ma_slow[-2], pp),
            'volume_1': round(volumes[-1], 0),
            'volume_2': round(volumes[-2], 0),
            'volume_3': round(volumes[-3], 0),
            'close_1': round(closes[-1], pp),
            'close_2': round(closes[-2], pp),
            'close_3': round(closes[-3], pp),
            'close_4': round(closes[-4], pp),
            'close_7': round(closes[-7], pp),
            'close_9': round(closes[-9], pp),
            'extreme_min': round(extreme_min, pp),
            'extreme_max': round(extreme_max, pp)
        }

        #print(ind)
        return ind

    async def get_indicators_advice(config, market, timeframe, reason):
        # try:
        #     if EXCHANGE == 'kucoinfutures':
        #         await connector.configure(config, market + ':' + market.split('/')[1])
        #     else:
        #         await connector.configure(config, market)
        # except Exception as e:
        #     log(market, '%s: %s %s' % ('CONFIGURE ERROR 02', type(e).__name__, str(e)))
        EXCHANGE = config.get_value("bot", "exchange")
        #LEVERAGE = float(config.get_value("bot", "leverage"))

        if EXCHANGE == 'bingx' and (market == 'FLOKI/USDT' or market == '1000FLOKI/USDT'):
            FLOKI = '1000FLOKI/USDT'
        else:
            FLOKI = 'FLOKI/USDT'
        if EXCHANGE == 'bybit' and (market == 'SHIB1000/USDT' or market == 'SHIB/USDT'):
            SHIB = 'SHIB1000/USDT'
        else:
            SHIB = 'SHIB/USDT'
        if EXCHANGE == 'bingx' and (market == 'TON/USDT' or market == 'TONCOIN/USDT'):
            TON = 'TONCOIN/USDT'
        else:
            TON = 'TON/USDT'
        #
        # symbol_list_1 = ['BTC/USDT', 'ETH/USDT', 'DOGE/USDT', 'MATIC/USDT', 'XRP/USDT', 'NEAR/USDT', 'AVAX/USDT', 'GALA/USDT', 'ONT/USDT', FLOKI, '1000PEPE/USDT', 'WIF/USDT', 'KAVA/USDT', 'LINK/USDT', 'ONDO/USDT']
        # symbol_list_2 = ['ETC/USDT', 'UNI/USDT', 'SOL/USDT', 'MANA/USDT', 'RNDR/USDT', 'SAND/USDT', 'GMT/USDT', TON, SHIB, 'DOT/USDT', 'STX/USDT', 'XTZ/USDT', 'NEO/USDT', 'IOTA/USDT', 'BAT/USDT']
        #
        # if market in symbol_list_1:
        #     server_url = 'http://185.128.107.45:8000'
        # elif market in symbol_list_2:
        #     server_url = 'http://109.205.212.69:8000'
        # else:
        #     server_url = None
        #
        # api_key = 'bmCQt2wEh5LG2YLq5x8pxZcw9Y1PJAvNTa7NyVtqrxzATPS9tVFRqsky7EjAg03I'


        if EXCHANGE == 'bingx':
            if market == 'FLOKI/USDT':
                m = '1000FLOKI/USDT'
            else:
                m = market

            if market == 'FLOKI/USDT':
                m = '1000FLOKI/USDT'
            else:
                m = market

            if market == 'SHIB/USDT':
                m = '1000SHIB/USDT'
            else:
                m = market

            if market == 'TONCOIN/USDT':
                m = 'TON/USDT'
            else:
                m = market
        else:
            m = market
        #
        #
        # if reason == "entry":
        #     MA_CROSS_MA1 = ENTRY_MA_CROSS_MA1
        #     MA_CROSS_MA2 = ENTRY_MA_CROSS_MA2
        # elif reason == "avg":
        #     MA_CROSS_MA1 = AVG_MA_CROSS_MA1
        #     MA_CROSS_MA2 = AVG_MA_CROSS_MA2
        # elif reason == "exit":
        #     MA_CROSS_MA1 = EXIT_MA_CROSS_MA1
        #     MA_CROSS_MA2 = EXIT_MA_CROSS_MA2
        # else:
        #     MA_CROSS_MA1 = AVG_MA_CROSS_MA1
        #     MA_CROSS_MA2 = AVG_MA_CROSS_MA2
        #
        #
        #
        # if server_url != None and (EMA200_LENGTH != 200 or MA_CROSS_MA1 != 25 or MA_CROSS_MA2 != 50 or FASTK_PERIOD != 14 or SLOWK_PERIOD != 4 or SLOWD_PERIOD != 3 or CCI_LENGTH != 20 or RSI_LENGTH != 14 or RSI_SMA_LENGTH != 3 or MACD_F != 12 or MACD_S != 26 or MACD_SIGNAL != 9 or BB_PERIOD != 20 or BB_DEV != 2 or ATR_LENGTH != 13 or EFI_LENGTH != 13 or EXTREMES_LEFT !=4 or EXTREMES_RIGHT != 3):
        #     #print(timeframe, 'Случай - пользовательские индикаторы по существующей паре')
        #     ohlcv_data = await fetch_ohlcv_data(server_url, 'bybit', [m], [timeframe], api_key)
        #     return calculate_ind(m, ohlcv_data, timeframe, reason)
        # elif server_url != None and EMA200_LENGTH == 200 and MA_CROSS_MA1 == 25 and MA_CROSS_MA2 == 50 and FASTK_PERIOD == 14 and SLOWK_PERIOD == 4 and SLOWD_PERIOD == 3 and CCI_LENGTH == 20 and RSI_LENGTH == 14 and RSI_SMA_LENGTH == 3 and MACD_F == 12 and MACD_S == 26 and MACD_SIGNAL == 9 and BB_PERIOD == 20 and BB_DEV == 2 and ATR_LENGTH == 13 and EFI_LENGTH == 13 and EXTREMES_LEFT ==4 and EXTREMES_RIGHT == 3:
        #     #print(timeframe, 'Случай - штатные индикаторы по существующей паре')
        #     ind_data = await fetch_ind_data(server_url, 'bybit', m, timeframe, api_key)
        #     json_string = ind_data[0]['data']
        #     p = json.loads(json_string)
        #
        #     ind = {
        #         'trend': p['trend'],
        #         'ema200': p['ema200'],
        #         'macd': p['macd'],
        #         'macd_signal': p['macd_signal'],
        #         'macd_h_1': p['macd_hist_1'],
        #         'macd_h_2': p['macd_hist_2'],
        #         'macd_h_3': p['macd_hist_3'],
        #         'macd_h_4': p['macd_hist_4'],
        #         'rsi_1': p['rsi_1'],
        #         'rsi_2': p['rsi_2'],
        #         'rsi_3': p['rsi_3'],
        #         'smarsi': p['sma_rsi'],
        #         'fast': p['stoch_fast'],
        #         'slow': p['stoch_slow'],
        #         'atr': p['atr_1'],
        #         'efi': p['efi_1'],
        #         'upper': p['bb_upper'],
        #         'middle': p['bb_middle'],
        #         'lower': p['bb_lower'],
        #         'cci_1': p['cci_1'],
        #         'cci_2': p['cci_2'],
        #         'cci_3': p['cci_3'],
        #         'ma_1_1': p['ma_fast_1'],
        #         'ma_2_1': p['ma_slow_1'],
        #         'ma_1_2': p['ma_fast_2'],
        #         'ma_2_2': p['ma_slow_2'],
        #         'volume_1': p['volume_1'],
        #         'volume_2': p['volume_2'],
        #         'volume_3': p['volume_3'],
        #         'close_1': p['close_1'],
        #         'close_2': p['close_2'],
        #         'close_3': p['close_3'],
        #         'close_4': p['close_4'],
        #         'close_7': p['close_7'],
        #         'close_9': p['close_9'],
        #         'extreme_min': p['extreme_min'],
        #         'extreme_max': p['extreme_max'],
        #     }
        #     #print(ind)
        #     return ind
        # # если пара не в списках
        # else:
        #print(timeframe, 'Случай - пара не всписках')
        _e = await connector.configure(config, m)
        ohlcv_data, price, error_msg = await connector.get_klines(_e, m, timeframe, 220)
        #print('3', ohlcv_data)
        return calculate_ind(m, ohlcv_data, timeframe, reason)

    # Функция increment_sell_counter увеличивает счетчик
    def increment_sell_counter(market):
        cursor.execute("""
            INSERT OR REPLACE INTO counters(
              counter_count,
              counter_market,
              orders_total
            ) 
            values(
              COALESCE((SELECT counter_count from counters WHERE counter_market=:counter_market), 0) + 1,
              :counter_market,
              :orders_total
            )
            """, {
            'counter_market': market,
            'orders_total': get_orders_total(market)
        })
        # print('QWER 1')
        cursor.execute("""
            UPDATE counters SET counter_count=0 WHERE counter_count > :orders_total AND counter_market=:counter_market
            """, {
            'counter_market': market,
            'orders_total': get_orders_total(market) - 1
        })
        # print('QWER 2')
        conn.commit()

    # Функция get_sell_counter получает счетчик
    def get_sell_counter(market):
        cursor.execute("""SELECT counter_count FROM counters WHERE counter_market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def if_buy_sell_count_filled(market, side):
        buy_or_sell_count_q = """
                SELECT
                   COUNT(*)
                FROM
                   orders
                WHERE
                   market='%s'
                   AND order_side = '%s'
                   AND order_filled IS NOT NULL
              """ % (market, side)
        cursor.execute(buy_or_sell_count_q)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]



    def record_trend(market, table, trend, flag, ask_price, bid_price, macdhist_1, macdhist_2, macdhist_3, macdhist_4, fast_stoch, slow_stoch, cci, ema200,
                     rsi, smarsi, atr, efi, ma_1, ma_2, upper, middle, lower, fast_global, slow_global, qfl_result, qfl_base):

        cursor.execute("""
            INSERT OR REPLACE INTO %s(
              market, trend, flag, ask_price, bid_price, macdhist_1, macdhist_2, macdhist_3, macdhist_4, fast_stoch, slow_stoch, cci, ema200, rsi, smarsi, atr, efi, ma_1, ma_2, upper, middle, lower, fast_global, slow_global, qfl_result, qfl_base
            ) 
            values(
              :market, :trend, :flag, :ask_price, :bid_price, :macdhist_1, :macdhist_2, :macdhist_3, :macdhist_4, :fast_stoch, :slow_stoch, :cci, :ema200, :rsi, :smarsi, :atr, :efi, :ma_1, :ma_2, :upper, :middle, :lower, :fast_global, :slow_global, :qfl_result, :qfl_base
            )
            """ % table, {
            'market': market, 'trend': trend, 'flag': flag, 'ask_price': ask_price, 'bid_price': bid_price, 'macdhist_1': macdhist_1, 'macdhist_2': macdhist_2, 'macdhist_3': macdhist_3,
            'macdhist_4': macdhist_4, 'fast_stoch': fast_stoch, 'slow_stoch': slow_stoch, 'cci': cci, 'ema200': ema200, 'rsi': rsi, 'smarsi': smarsi, 'atr': atr, 'efi': efi, 'ma_1': ma_1,
            'ma_2': ma_2, 'upper': upper, 'middle': middle, 'lower': lower, 'fast_global': fast_global, 'slow_global': slow_global, 'qfl_result': qfl_result, 'qfl_base': qfl_base
        })
        conn.commit()

    # def record_qfl(market, table, qfl_result, qfl_base):
    #     cursor.execute("""INSERT OR REPLACE INTO %s(qfl_result, qfl_base) values(:qfl_result, :qfl_base)""" % table, {'qfl_result': qfl_result, 'qfl_base': qfl_base})
    #     conn.commit()

    def record_timeframe(market, timeframe_switch, initial_tf, initial_stoch_long, initial_stoch_short, ema_reason, order_count_reason, candle_count_reason, stoch_reason):
        cursor.execute("""
            INSERT OR REPLACE INTO timeframe(
               market, timeframe_switch, initial_tf, initial_stoch_long, initial_stoch_short, ema_reason, order_count_reason, candle_count_reason, stoch_reason
            ) 
            values(
               :market, :timeframe_switch, :initial_tf, :initial_stoch_long, :initial_stoch_short, :ema_reason, :order_count_reason, :candle_count_reason, :stoch_reason
            )
            """, {
            'market': market, 'timeframe_switch': timeframe_switch, 'initial_tf': initial_tf,
            'initial_stoch_long': initial_stoch_long, 'initial_stoch_short': initial_stoch_short, 'ema_reason': ema_reason,
            'order_count_reason': order_count_reason, 'candle_count_reason': candle_count_reason,
            'stoch_reason': stoch_reason
        })
        conn.commit()

    def get_flag(market, table):
        cursor.execute("""SELECT flag FROM %s WHERE market='%s'""" % (table, market))
        result = cursor.fetchone()
        if not result or not result[0]:
            return "0"
        return result[0]

    def get_price_last(market, side):
        cursor.execute("""
          SELECT
              order_price
          FROM
              orders
          WHERE
              market='%s'
              AND order_side='%s'
              AND order_cancelled IS NULL
              AND order_filled IS NOT NULL
          ORDER BY order_created DESC
          LIMIT 1
        """ % (market, side))
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_cost_last(market, side):
        price_last_q = """
          SELECT
              order_cost
          FROM
              orders
          WHERE
              market='%s'
              AND order_side='%s'
              AND order_filled IS NOT NULL
              AND order_cancelled IS NULL
          ORDER BY order_created DESC
          LIMIT 1
        """ % (market, side)
        cursor.execute(price_last_q)
        return cursor.fetchone()[0]

    def get_date_last(market, side):
        cursor.execute("""
          SELECT
              order_filled
          FROM
              orders
          WHERE
              market='%s'
              AND order_side='%s'
              AND order_filled IS NOT NULL
          ORDER BY order_created DESC
          LIMIT 1
        """ % (market, side))
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_deal_number(market):
        cursor.execute("""
               SELECT
                 deal_number
               FROM
                 orders
               WHERE
                 market=:market
               ORDER BY order_created DESC
        """, {
            'market': market
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_open_stop_order(market, side, deal_number):
        cursor.execute("""
               SELECT
                 order_id
               FROM
                 orders
               WHERE
                 market=:market
                 AND stop_loss=1
                 AND order_side=:side
                 AND deal_number=:deal_number
                 AND order_cancelled IS NULL
                 AND order_filled IS NULL
               ORDER BY order_created ASC
        """, {
            'market': market,
            'side': side,
            'deal_number': deal_number
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_base_order_date(market, side, deal_number):
        cursor.execute("""
               SELECT
                 order_created
               FROM
                 orders
               WHERE
                 market=:market
                 AND order_side=:side
                 AND deal_number=:deal_number
                 AND order_cancelled IS NULL
               ORDER BY order_created ASC
        """, {
            'market': market,
            'side': side,
            'deal_number': deal_number
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_base_order_price(market, side, deal_number):
        cursor.execute("""
               SELECT
                 order_price
               FROM
                 orders
               WHERE
                 market=:market
                 AND order_side=:side
                 AND deal_number=:deal_number
                 AND order_cancelled IS NULL
               ORDER BY order_created ASC
        """, {
            'market': market,
            'side': side,
            'deal_number': deal_number
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_base_order_cost(market, side, deal_number):
        cursor.execute("""
               SELECT
                 order_cost
               FROM
                 orders
               WHERE
                 market=:market
                 AND order_side=:side
                 AND deal_number=:deal_number
                 AND order_cancelled IS NULL
               ORDER BY order_created ASC
        """, {
            'market': market,
            'side': side,
            'deal_number': deal_number
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_base_order_balance(market, side, deal_number):
        cursor.execute("""
               SELECT
                 balance
               FROM
                 orders
               WHERE
                 market=:market
                 AND order_side=:side
                 AND deal_number=:deal_number
                 AND order_cancelled IS NULL
               ORDER BY order_created ASC
        """, {
            'market': market,
            'side': side,
            'deal_number': deal_number
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_base_order_state(market, deal_number):
        cursor.execute(
            """SELECT order_id FROM orders WHERE market='%s' AND deal_number='%s' AND order_cancelled IS NULL ORDER BY order_created ASC""" % (market, deal_number))
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_algo(market, deal_number):
        cursor.execute(
            """SELECT order_strategy FROM orders WHERE market='%s' AND deal_number='%s' ORDER BY order_created DESC""" % (market, deal_number))
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def deal_profit(market, side):
        if side == 'buy':
            anti_side = 'sell'
        else:
            anti_side = 'buy'

        deal_number = get_deal_number(market)

        baseCurrency = market.split('/')[0]
        quoteCurrency = market.split('/')[1]

        deal_buy_spent_long_q = """
              SELECT
                  SUM(order_cost)
              FROM
                  orders
              WHERE
                  market='%s'
                  AND order_side='%s'
                  AND deal_number='%s'
                  AND order_filled IS NOT NULL
                  AND order_cancelled IS NULL
            """ % (market, side, deal_number)
        cursor.execute(deal_buy_spent_long_q)
        deal_buy_spent_long = cursor.fetchone()
        if not deal_buy_spent_long or not deal_buy_spent_long[0]:
            deal_buy_spent_long = 0
        else:
            deal_buy_spent_long = deal_buy_spent_long[0]

        deal_sell_spent_long_q = """
              SELECT
                  SUM(order_cost)
              FROM
                  orders
              WHERE
                  market='%s'
                  AND order_side='%s'
                  AND deal_number='%s'
                  AND order_filled IS NOT NULL
            """ % (market, anti_side, deal_number)
        cursor.execute(deal_sell_spent_long_q)
        deal_sell_spent_long = cursor.fetchone()
        if not deal_sell_spent_long or not deal_sell_spent_long[0]:
            deal_sell_spent_long = 0
        else:
            deal_sell_spent_long = deal_sell_spent_long[0]

        buy_o_spent_long_q = """
              SELECT
                  SUM(order_cost)
              FROM
                  orders
              WHERE
                  market='%s'
                  AND order_side='%s'
                  AND order_filled IS NOT NULL
                  AND order_cancelled IS NULL
            """ % (market, side)
        cursor.execute(buy_o_spent_long_q)
        buy_o_spent_long = cursor.fetchone()
        if not buy_o_spent_long or not buy_o_spent_long[0]:
            buy_o_spent_long = 0
        else:
            buy_o_spent_long = buy_o_spent_long[0]

        sell_o_spent_long_q = """
              SELECT
                  SUM(order_cost)
              FROM
                  orders
              WHERE
                  market='%s'
                  AND order_side='%s'
                  AND order_filled IS NOT NULL
            """ % (market, anti_side)
        cursor.execute(sell_o_spent_long_q)
        sell_o_spent_long = cursor.fetchone()
        if not sell_o_spent_long or not sell_o_spent_long[0]:
            sell_o_spent_long = 0
        else:
            sell_o_spent_long = sell_o_spent_long[0]

        price_sell_long_q = """
              SELECT
                  order_price
              FROM
                  orders
              WHERE
                  market='%s'
                  AND order_side='%s'
                  AND order_filled IS NOT NULL
              ORDER BY order_created DESC
            """ % (market, anti_side)
        cursor.execute(price_sell_long_q)
        price_sell_long = cursor.fetchone()
        if price_sell_long != None:
            price_sell_long = price_sell_long[0]
        else:
            price_sell_long = 1

        bought = round(buy_o_spent_long, 8)
        sold = round(sell_o_spent_long, 8)

        deal_bought = round(deal_buy_spent_long, 8)
        deal_sold = round(deal_sell_spent_long, 8)

        if side == 'buy':
            profit_mail = sold - bought
            profit_deal_mail = deal_sold - deal_bought
            if deal_bought == 0:
                profit_deal_percent = 0
            else:
                profit_deal_percent = round(profit_deal_mail / deal_bought * 100, 2)

        else:
            profit_mail = bought - sold
            profit_deal_mail = deal_bought - deal_sold
            if deal_sold == 0:
                profit_deal_percent = 0
            else:
                profit_deal_percent = round(profit_deal_mail / deal_sold * 100, 2)

        currency = quoteCurrency
        return [profit_deal_mail, profit_deal_percent, profit_mail, currency]

    def open_orders_count(market, side):
        deal_number = get_deal_number(market)
        #print('deal_number',deal_number)
        orders_count_q = """
                SELECT
                   COUNT(*)
                FROM
                   orders
                WHERE
                   market='%s'
                   AND order_side = '%s'
                   AND deal_number = '%s'
                   AND order_filled IS NULL
                   AND order_cancelled IS NULL
              """ % (market, side, deal_number)
        cursor.execute(orders_count_q)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def deal_length(market, start_side):
        deal_number = get_deal_number(market)
        orders_count_q = """
                SELECT
                   COUNT(*)
                FROM
                   orders
                WHERE
                   market='%s'
                   AND order_side = '%s'
                   AND deal_number = '%s'
                   AND order_filled IS NOT NULL
              """ % (market, start_side, deal_number)
        cursor.execute(orders_count_q)
        result = cursor.fetchone()
        if not result or not result[0]:
            orders_count = 0
        else:
            orders_count = result[0]

        if start_side == 'buy':
            end_side = 'sell'
        else:
            end_side = 'buy'

        start_date = datetime.strptime(get_base_order_date(market, start_side, deal_number), '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(get_date_last(market, end_side), '%Y-%m-%d %H:%M:%S')

        if abs(end_date - start_date).days > 0:
            s_days = str(abs(end_date - start_date)).split(',')[0].split(' ')[0]
            h_m_s = str(abs(end_date - start_date)).split(',')[1].replace(' ', '').split(':')
            s_hours = h_m_s[0]
            s_minutes = h_m_s[1]
            s_seconds = h_m_s[2]
        else:
            s_days = '0'
            h_m_s = str(abs(end_date - start_date)).split(':')
            s_hours = h_m_s[0]
            s_minutes = h_m_s[1]
            s_seconds = h_m_s[2]

        if s_days == '0':
            if s_hours == '0':
                return LANGUAGES[LANG]["deal_duration"] + ' ' + str(s_minutes) + ' ' + LANGUAGES[LANG]["minutes"] + ' ' + str(s_seconds) + ' ' + LANGUAGES[LANG]["seconds"] + ' ' + LANGUAGES[LANG]["test_spent"] + ' ' + str(orders_count) + ' ' + LANGUAGES[LANG]["orders_spent"]
            else:
                return LANGUAGES[LANG]["deal_duration"] + ' ' + str(s_hours) + ' ' + LANGUAGES[LANG]["hours"] + ' ' + str(s_minutes) + ' ' + LANGUAGES[LANG]["minutes"] + ' ' + str(s_seconds) + ' ' + LANGUAGES[LANG]["seconds"] + ' ' + LANGUAGES[LANG]["test_spent"] + ' ' + str(orders_count) + ' ' + LANGUAGES[LANG]["orders_spent"]
        else:
            return LANGUAGES[LANG]["deal_duration"] + ' ' + str(s_days) + ' ' + LANGUAGES[LANG]["days"] + ' ' + str(s_hours) + ' ' + LANGUAGES[LANG]["hours"] + ' ' + str(s_minutes) + ' ' + LANGUAGES[LANG]["minutes"] + ' ' + str(s_seconds) + ' ' + LANGUAGES[LANG]["seconds"] + ' ' + LANGUAGES[LANG]["test_spent"] + ' ' + str(orders_count) + ' ' + LANGUAGES[LANG]["orders_spent"]

    def sum_order_spent(market, side, limit):
        cursor.execute("""
                SELECT
                   SUM(order_cost)
                FROM (
                   SELECT
                     order_cost,
                     order_filled
                   FROM
                     orders
                   WHERE
                     market=:market
                     AND order_side=:side
                   ORDER BY order_created DESC
                   LIMIT :orders_total
                ) WHERE order_filled IS NOT NULL
             """, {
            'side': side,
            'market': market,
            'orders_total': limit
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def sum_order_amount(market, side, limit):
        cursor.execute("""
                SELECT
                   SUM(order_amount)
                FROM (
                   SELECT
                     order_amount,
                     order_filled
                   FROM
                     orders
                   WHERE
                     market=:market
                     AND order_side=:side
                   ORDER BY order_created DESC
                   LIMIT :orders_total
                ) WHERE order_filled IS NOT NULL
             """, {
            'side': side,
            'market': market,
            'orders_total': limit
        })
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def if_not_filled_buy(market, side):
        not_filled_buy_q = """
               SELECT
                  order_id
               FROM
                  orders
               WHERE
                  market='%s'
                  AND order_side='%s'
                  AND order_filled IS NULL
                  AND order_cancelled IS NULL
               ORDER BY order_created DESC
               LIMIT 1
             """ % (market, side)
        cursor.execute(not_filled_buy_q)
        result = cursor.fetchone()
        if not result or not result[0]:
            return None
        return result[0]

    def if_tf_switched(market):
        cursor.execute("""SELECT timeframe_switch FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_initial_tf(market):
        cursor.execute("""SELECT initial_tf FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_initial_stoch_long(market):
        cursor.execute("""SELECT initial_stoch_long FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_initial_stoch_short(market):
        cursor.execute("""SELECT initial_stoch_short FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_ema_reason(market):
        cursor.execute("""SELECT ema_reason FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_order_count_reason(market):
        cursor.execute("""SELECT order_count_reason FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_candle_count_reason(market):
        cursor.execute("""SELECT candle_count_reason FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def get_stoch_reason(market):
        cursor.execute("""SELECT stoch_reason FROM timeframe WHERE market='%s'""" % market)
        result = cursor.fetchone()
        if not result or not result[0]:
            return 0
        return result[0]

    def cancel_order_id(order):
        cursor.execute("""UPDATE orders SET order_cancelled=datetime() WHERE order_id = :order_id""", {'order_id': order})
        conn.commit()

    def get_orders_total(market):
        cursor.execute("""SELECT orders_total FROM counters WHERE counter_market='%s'""" % (market))
        result = cursor.fetchone()
        if not result or not result[0]:
            return config.get_value("bot", "orders_total")
        return result[0]

    def get_bp(k, s):
        #Функция вычисления бэкпрофита в зависимости от sell_count
        integer_part, fractional_part = str(k).split('.')
        integer_part = int(integer_part)
        fractional_part = float('0.' + fractional_part)

        result = s * fractional_part

        new_integer_part = integer_part + int(result)
        new_fractional_part = result - int(result)

        return new_integer_part + new_fractional_part

    def log(*args):
        logger.info(" ".join([str(x) for x in args]))

    # ПРЕСЕТЫ
    def get_global_stoch_answer(reason, side, fast_global, slow_global):
        if side == None:
            GLOBAL_STOCH_ALLOWS = False

        if side == 'buy':
            GLOBAL_STOCH_UP_LEVEL = GLOBAL_STOCH_LONG_UP_LEVEL
            GLOBAL_STOCH_LOW_LEVEL = GLOBAL_STOCH_LONG_LOW_LEVEL
        else:
            GLOBAL_STOCH_UP_LEVEL = GLOBAL_STOCH_SHORT_UP_LEVEL
            GLOBAL_STOCH_LOW_LEVEL = GLOBAL_STOCH_SHORT_LOW_LEVEL

        if reason == 'exit':
            USE_GLOBAL_STOCH = False
        else:
            USE_GLOBAL_STOCH = config.get_value("indicators_tuning", "use_global_stoch")

        if USE_GLOBAL_STOCH == True and side != None:
            # if ((((reason == 'entry' or reason == 'avg') and side == 'buy')) and fast_global > slow_global) or (
            #         (((reason == 'entry' or reason == 'avg') and side == 'sell')) and fast_global < slow_global):
            #     GLOBAL_FAST_SLOW_ALLOWS = True
            # else:
            #     GLOBAL_FAST_SLOW_ALLOWS = False

            GLOBAL_FAST_SLOW_ALLOWS = True # Переделано на более простое условие - присутствие в канале. Выше - код где ждем пересечение
            if GLOBAL_STOCH_LOW_LEVEL < fast_global < GLOBAL_STOCH_UP_LEVEL and GLOBAL_FAST_SLOW_ALLOWS == True:
                GLOBAL_STOCH_ALLOWS = True
                # log(market, "global_stoch_allows")
            else:
                GLOBAL_STOCH_ALLOWS = False
                # log(market, "global_stoch_not_allows")
        else:
            GLOBAL_STOCH_ALLOWS = True

        return GLOBAL_STOCH_ALLOWS

    def get_stoch_cci_answer(market, reason, side, **kwargs):
        if side == None:
            STOCH_ALLOWS = False
            CCI_ALLOWS = False
            GLOBAL_STOCH_ALLOWS = False
        else:
            STOCH_ALLOWS = False
            CCI_ALLOWS = False

            fast_stoch = kwargs['fast_stoch']
            slow_stoch = kwargs['slow_stoch']

            fast_global = kwargs['fast_global']
            slow_global = kwargs['slow_global']

            cci = kwargs['cci']
            cci_2 = kwargs['cci_2']
            cci_3 = kwargs['cci_3']

            if reason == 'entry':
                USE_STOCH = ENTRY_USE_STOCH_C
                USE_CCI = ENTRY_USE_CCI
                BASIC_INDICATOR = ENTRY_BASIC_INDICATOR_C
                if side == 'buy':
                    STOCH_UP_LEVEL = ENTRY_STOCH_C_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = ENTRY_STOCH_C_LONG_LOW_LEVEL
                    CCI_LEVEL = ENTRY_CCI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = ENTRY_STOCH_C_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = ENTRY_STOCH_C_SHORT_LOW_LEVEL
                    CCI_LEVEL = ENTRY_CCI_SHORT_LEVEL

            if reason == 'avg':
                USE_STOCH = AVG_USE_STOCH_C
                USE_CCI = AVG_USE_CCI
                BASIC_INDICATOR = AVG_BASIC_INDICATOR_C
                if side == 'buy':
                    STOCH_UP_LEVEL = AVG_STOCH_C_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = AVG_STOCH_C_LONG_LOW_LEVEL
                    CCI_LEVEL = AVG_CCI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = AVG_STOCH_C_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = AVG_STOCH_C_SHORT_LOW_LEVEL
                    CCI_LEVEL = AVG_CCI_SHORT_LEVEL

            if reason == 'exit':
                USE_STOCH = EXIT_USE_STOCH_C
                USE_CCI = EXIT_USE_CCI
                BASIC_INDICATOR = EXIT_BASIC_INDICATOR_C
                if side == 'buy':
                    STOCH_UP_LEVEL = EXIT_STOCH_C_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = EXIT_STOCH_C_LONG_LOW_LEVEL
                    CCI_LEVEL = EXIT_CCI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = EXIT_STOCH_C_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = EXIT_STOCH_C_SHORT_LOW_LEVEL
                    CCI_LEVEL = EXIT_CCI_SHORT_LEVEL

            if ((((reason == 'entry' or reason == 'avg') and side == 'buy') or (reason == 'exit' and side == 'sell')) and fast_stoch > slow_stoch) or ((((reason == 'entry' or reason == 'avg') and side == 'sell') or ( reason == 'exit' and side == 'buy')) and fast_stoch < slow_stoch):
                FAST_SLOW_ALLOWS = True
            else:
                FAST_SLOW_ALLOWS = False

            #print('FAST_SLOW_ALLOWS',FAST_SLOW_ALLOWS)

            if (USE_GLOBAL_STOCH == False and ((
                        USE_CCI == True and BASIC_INDICATOR == 'stoch' and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True) or (
                        USE_CCI == True and BASIC_INDICATOR == 'cci' and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL) or (
                        USE_CCI == False and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True))) or (
                USE_GLOBAL_STOCH == True and ((
                        USE_CCI == True and BASIC_INDICATOR == 'stoch' and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True) or (
                        USE_CCI == True and BASIC_INDICATOR == 'cci' and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL) or (
                        USE_CCI == False and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True))):
                STOCH_ALLOWS = True

            if USE_STOCH == False:
                STOCH_ALLOWS = True

            #print('STOCH_ALLOWS', STOCH_ALLOWS)

            if ((reason == 'entry' or reason == 'avg') and side == 'buy') or (reason == 'exit' and side == 'sell'):
                if (USE_STOCH == True and BASIC_INDICATOR == 'stoch' and cci_2 < CCI_LEVEL) or (BASIC_INDICATOR == 'cci' and cci_2 < CCI_LEVEL and cci_3 > cci_2 and cci > cci_2):
                    CCI_ALLOWS = True
                elif USE_CCI == False:
                    CCI_ALLOWS = True
                else:
                    CCI_ALLOWS = False

            if ((reason == 'entry' or reason == 'avg') and side == 'sell') or (reason == 'exit' and side == 'buy'):
                if (USE_STOCH == True and BASIC_INDICATOR == 'stoch' and cci_2 > CCI_LEVEL) or (BASIC_INDICATOR == 'cci' and cci_2 > CCI_LEVEL and cci_3 < cci_2 and cci < cci_2):
                    CCI_ALLOWS = True
                elif USE_CCI == False:
                    CCI_ALLOWS = True
                else:
                    CCI_ALLOWS = False

            GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, side, fast_global, slow_global)

        return STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS


    def get_stoch_rsi_answer(market, reason, side, **kwargs):
        if side == None:
            STOCH_ALLOWS = False
            RSI_ALLOWS = False
            GLOBAL_STOCH_ALLOWS = False
        else:
            STOCH_ALLOWS = False
            RSI_ALLOWS = False

            fast_stoch = kwargs['fast_stoch']
            slow_stoch = kwargs['slow_stoch']

            fast_global = kwargs['fast_global']
            slow_global = kwargs['slow_global']

            rsi = kwargs['rsi']
            rsi_2 = kwargs['rsi_2']
            rsi_3 = kwargs['rsi_3']

            if reason == 'entry':
                USE_STOCH = ENTRY_USE_STOCH_S
                USE_RSI = ENTRY_USE_RSI
                BASIC_INDICATOR = ENTRY_BASIC_INDICATOR_S
                if side == 'buy':
                    STOCH_UP_LEVEL = ENTRY_STOCH_S_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = ENTRY_STOCH_S_LONG_LOW_LEVEL
                    RSI_LEVEL = ENTRY_RSI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = ENTRY_STOCH_S_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = ENTRY_STOCH_S_SHORT_LOW_LEVEL
                    RSI_LEVEL = ENTRY_RSI_SHORT_LEVEL

            if reason == 'avg':
                USE_STOCH = AVG_USE_STOCH_S
                USE_RSI = AVG_USE_RSI
                BASIC_INDICATOR = AVG_BASIC_INDICATOR_S
                if side == 'buy':
                    STOCH_UP_LEVEL = AVG_STOCH_S_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = AVG_STOCH_S_LONG_LOW_LEVEL
                    RSI_LEVEL = AVG_RSI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = AVG_STOCH_S_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = AVG_STOCH_S_SHORT_LOW_LEVEL
                    RSI_LEVEL = AVG_RSI_SHORT_LEVEL

            if reason == 'exit':
                USE_STOCH = EXIT_USE_STOCH_S
                USE_RSI = EXIT_USE_RSI
                BASIC_INDICATOR = EXIT_BASIC_INDICATOR_S
                if side == 'buy':
                    STOCH_UP_LEVEL = EXIT_STOCH_S_LONG_UP_LEVEL
                    STOCH_LOW_LEVEL = EXIT_STOCH_S_LONG_LOW_LEVEL
                    RSI_LEVEL = EXIT_RSI_LONG_LEVEL
                else:
                    STOCH_UP_LEVEL = EXIT_STOCH_S_SHORT_UP_LEVEL
                    STOCH_LOW_LEVEL = EXIT_STOCH_S_SHORT_LOW_LEVEL
                    RSI_LEVEL = EXIT_RSI_SHORT_LEVEL

            if ((((reason == 'entry' or reason == 'avg') and side == 'buy') or (reason == 'exit' and side == 'sell')) and fast_stoch > slow_stoch) or ((((reason == 'entry' or reason == 'avg') and side == 'sell') or (reason == 'exit' and side == 'buy')) and fast_stoch < slow_stoch):
                FAST_SLOW_ALLOWS = True
            else:
                FAST_SLOW_ALLOWS = False

            #print('FAST_SLOW_ALLOWS',FAST_SLOW_ALLOWS)

            if (USE_GLOBAL_STOCH == False and ((
                            USE_RSI == True and BASIC_INDICATOR == 'stoch' and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True) or (
                            USE_RSI == True and BASIC_INDICATOR == 'rsi' and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL) or (
                            USE_RSI == False and STOCH_LOW_LEVEL < slow_stoch < STOCH_UP_LEVEL and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True))) or (
                USE_GLOBAL_STOCH == True and ((
                            USE_RSI == True and BASIC_INDICATOR == 'stoch' and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True) or (
                            USE_RSI == True and BASIC_INDICATOR == 'rsi' and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL) or (
                            USE_RSI == False and STOCH_LOW_LEVEL < fast_stoch < STOCH_UP_LEVEL and FAST_SLOW_ALLOWS == True))):
                STOCH_ALLOWS = True

            elif USE_STOCH == False:
                STOCH_ALLOWS = True


            #print('STOCH_ALLOWS', STOCH_ALLOWS)

            if ((reason == 'entry' or reason == 'avg') and side == 'buy') or (reason == 'exit' and side == 'sell'):
                if (USE_STOCH == True and BASIC_INDICATOR == 'stoch' and rsi_2 < RSI_LEVEL) or (BASIC_INDICATOR == 'rsi' and rsi_2 < RSI_LEVEL and rsi_3 > rsi_2 and rsi > rsi_2):
                    RSI_ALLOWS = True
                elif USE_RSI == False:
                    RSI_ALLOWS = True
                else:
                    RSI_ALLOWS = False

            if ((reason == 'entry' or reason == 'avg') and side == 'sell') or (reason == 'exit' and side == 'buy'):
                if (USE_STOCH == True and BASIC_INDICATOR == 'stoch' and rsi_2 > RSI_LEVEL) or (BASIC_INDICATOR == 'rsi' and rsi_2 > RSI_LEVEL and rsi_3 < rsi_2 and rsi < rsi_2):
                    RSI_ALLOWS = True
                elif USE_RSI == False:
                    RSI_ALLOWS = True
                else:
                    RSI_ALLOWS = False

            GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, side, fast_global, slow_global)

        return STOCH_ALLOWS, RSI_ALLOWS, GLOBAL_STOCH_ALLOWS


    def get_cci_cross_answer(market, reason, side, **kwargs):
        current_price = kwargs['current_price']
        cci = kwargs['cci']
        cci_2 = kwargs['cci_2']
        slow_global = kwargs['slow_global']
        fast_global = kwargs['fast_global']

        CCI_CROSS_ALLOWS = False
        GLOBAL_STOCH_ALLOWS = False
        GLOBAL_FAST_SLOW_ALLOWS = False

        if reason == 'entry':
            table = "trend_entry"
            USE_PRICE = ENTRY_CCI_CROSS_USE_PRICE
            CCI_CROSS_METHOD = ENTRY_CCI_CROSS_METHOD
            cci_cross_allows = LANGUAGES[LANG]["log_cci_cross_allows_entry"]
            cci_cross_not_allows = LANGUAGES[LANG]["log_cci_cross_not_allows_entry"]
            if side == 'buy':
                price = 'ask_price'
                CCI_LEVEL = ENTRY_CCI_CROSS_LONG_LEVEL
            else:
                price = 'bid_price'
                CCI_LEVEL = ENTRY_CCI_CROSS_SHORT_LEVEL

        if reason == 'avg':
            table = "trend_avg"
            USE_PRICE = AVG_CCI_CROSS_USE_PRICE
            CCI_CROSS_METHOD = AVG_CCI_CROSS_METHOD
            cci_cross_allows = LANGUAGES[LANG]["log_cci_cross_allows_avg"]
            cci_cross_not_allows = LANGUAGES[LANG]["log_cci_cross_not_allows_avg"]
            if side == 'buy':
                price = 'ask_price'
                CCI_LEVEL = AVG_CCI_CROSS_LONG_LEVEL

            else:
                price = 'bid_price'
                CCI_LEVEL = AVG_CCI_CROSS_SHORT_LEVEL


        if reason == 'exit':
            table = "trend_exit"
            USE_PRICE = EXIT_CCI_CROSS_USE_PRICE
            CCI_CROSS_METHOD = EXIT_CCI_CROSS_METHOD
            cci_cross_allows = LANGUAGES[LANG]["log_cci_cross_allows_exit"]
            cci_cross_not_allows = LANGUAGES[LANG]["log_cci_cross_not_allows_exit"]
            if side == 'buy':
                price = 'bid_price'
                CCI_LEVEL = EXIT_CCI_CROSS_LONG_LEVEL

            else:
                price = 'ask_price'
                CCI_LEVEL = EXIT_CCI_CROSS_SHORT_LEVEL


        last_cycle_price = """SELECT %s FROM %s WHERE market='%s'""" % (price, table, market)
        cursor.execute(last_cycle_price)
        last_cycle_price_q = cursor.fetchone()
        if not last_cycle_price_q or not last_cycle_price_q[0]:
            last_cycle_price = current_price
        else:
            last_cycle_price = float(last_cycle_price_q[0])

        last_cycle_cci = """SELECT cci FROM %s WHERE market='%s'""" % (table, market)
        cursor.execute(last_cycle_cci)
        last_cycle_cci_q = cursor.fetchone()
        if not last_cycle_cci_q or not last_cycle_cci_q[0]:
            last_cycle_cci = cci_2
        else:
            last_cycle_cci = float(last_cycle_cci_q[0])

        # if side == 'buy':
        #     CCI_CROSS_METHOD == "crossover"
        # else:
        #     CCI_CROSS_METHOD == "crossunder"

        if USE_PRICE == True:
            log(market, "%s: %s. %s: %s" % (
            LANGUAGES[LANG]["log_previous_price"], last_cycle_price, LANGUAGES[LANG]["log_current_price"], current_price))
            log(market, "%s: %.3f. %s: %.3f" % (
            LANGUAGES[LANG]["log_previous_cci"], last_cycle_cci, LANGUAGES[LANG]["log_current_cci"], cci))
            # log(market, "CCI_LEVEL =", CCI_LEVEL)
            if (((reason == 'exit' and side == 'buy') or (
                    (
                            reason == 'entry' or reason == 'avg') and side == 'sell')) and last_cycle_price != 0 and last_cycle_price > current_price and last_cycle_cci > cci and cci > CCI_LEVEL) or \
                    (((reason == 'exit' and side == 'sell') or (
                            (
                                    reason == 'entry' or reason == 'avg') and side == 'buy')) and last_cycle_price != 0 and last_cycle_price < current_price and last_cycle_cci < cci and cci < CCI_LEVEL):
                CCI_CROSS_ALLOWS = True
                log(market, cci_cross_allows)
            else:
                CCI_CROSS_ALLOWS = False
                log(market, cci_cross_not_allows)
        else:
            log(market, "%s: %.3f. %s: %.3f" % (
            LANGUAGES[LANG]["log_previous_cci"], last_cycle_cci, LANGUAGES[LANG]["log_current_cci"], cci))
            # log(market, "CCI_LEVEL =", CCI_LEVEL)
            if (side == 'buy' and last_cycle_cci < CCI_LEVEL and cci > CCI_LEVEL) or (side == 'sell' and last_cycle_cci > CCI_LEVEL and cci < CCI_LEVEL):
                CCI_CROSS_ALLOWS = True
                log(market, cci_cross_allows)
            else:
                CCI_CROSS_ALLOWS = False
                log(market, cci_cross_not_allows)

        GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, side, fast_global, slow_global)

        return CCI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS


    def get_rsi_smarsi_cross_answer(market, reason, side, **kwargs):
        current_price = kwargs['current_price']
        rsi = kwargs['rsi']
        smarsi = kwargs['smarsi']
        slow_global = kwargs['slow_global']
        fast_global = kwargs['fast_global']

        RSI_SMARSI_CROSS_ALLOWS = False

        if reason == 'entry':
            if side == 'buy':
                UP_LEVEL = ENTRY_SMARSI_CROSS_LONG_UP_LEVEL
                LOW_LEVEL = ENTRY_SMARSI_CROSS_LONG_LOW_LEVEL
            else:
                UP_LEVEL = ENTRY_SMARSI_CROSS_SHORT_UP_LEVEL
                LOW_LEVEL = ENTRY_SMARSI_CROSS_SHORT_LOW_LEVEL

        if reason == 'avg':
            if side == 'buy':
                UP_LEVEL = AVG_SMARSI_CROSS_LONG_UP_LEVEL
                LOW_LEVEL = AVG_SMARSI_CROSS_LONG_LOW_LEVEL
            else:
                UP_LEVEL = AVG_SMARSI_CROSS_SHORT_UP_LEVEL
                LOW_LEVEL = AVG_SMARSI_CROSS_SHORT_LOW_LEVEL

        if reason == 'exit':
            if side == 'buy':
                UP_LEVEL = EXIT_SMARSI_CROSS_LONG_UP_LEVEL
                LOW_LEVEL = EXIT_SMARSI_CROSS_LONG_LOW_LEVEL
            else:
                UP_LEVEL = EXIT_SMARSI_CROSS_SHORT_UP_LEVEL
                LOW_LEVEL = EXIT_SMARSI_CROSS_SHORT_LOW_LEVEL

        log(market, "%s: %.3f, %.3f" % (LANGUAGES[LANG]["log_current_rsi"], rsi, smarsi))

        if (((reason == 'exit' and side == 'buy') or (
                (
                        reason == 'entry' or reason == 'avg') and side == 'sell')) and LOW_LEVEL < rsi < UP_LEVEL and LOW_LEVEL < smarsi < UP_LEVEL and rsi < smarsi) or \
                (((reason == 'exit' and side == 'sell') or (
                        (
                                reason == 'entry' or reason == 'avg') and side == 'buy')) and LOW_LEVEL < rsi < UP_LEVEL and LOW_LEVEL < smarsi < UP_LEVEL and rsi > smarsi):
            RSI_SMARSI_CROSS_ALLOWS = True

        else:
            if reason == 'entry': log(market, "%s %s" % ("RSI_SMARSI", LANGUAGES[LANG]["log_stoch_not_allows"]))
            if reason == 'avg': log(market, "%s %s" % ("RSI_SMARSI", LANGUAGES[LANG]["log_xxx_not_allows_avg"]))
            if reason == 'exit': log(market, "%s %s" % ("RSI_SMARSI", LANGUAGES[LANG]["log_price_not_allows_exit"]))

        GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, side, fast_global, slow_global)

        return RSI_SMARSI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS

    def get_midas_answer(market, reason, **kwargs):
        MIDAS_ALLOWS = False

        current_price = kwargs['current_price']
        old_qfl = kwargs['old_qfl']
        old_base = kwargs['old_base']
        #slow_global = kwargs['slow_global']
        #fast_global = kwargs['fast_global']

        if reason == 'entry':
            table = "trend_entry"
            #QFL_CROSS_METHOD = ENTRY_MA_CROSS_METHOD
            H_L_PERCENT = ENTRY_H_L_PERCENT

        if reason == 'avg':
            table = "trend_avg"
            #QFL_CROSS_METHOD = AVG_MA_CROSS_METHOD
            H_L_PERCENT = AVG_H_L_PERCENT

        if reason == 'exit':
            table = "trend_exit"
            #QFL_CROSS_METHOD = EXIT_MA_CROSS_METHOD
            H_L_PERCENT = EXIT_H_L_PERCENT

        if EXCHANGE != 'binance':
            if old_qfl == 'buy':
                price = 'ask_price'
            else:
                price = 'bid_price'
        else:
            price = 'ask_price'

        cursor.execute("""SELECT %s FROM %s WHERE market='%s'""" % (price, table, market))
        last_cycle_price_q = cursor.fetchone()
        if not last_cycle_price_q or not last_cycle_price_q[0]:
            last_cycle_price = current_price
        else:
            last_cycle_price = float(last_cycle_price_q[0])

        cursor.execute("""SELECT price_precision FROM limits WHERE market='%s'""" % market)
        pricePrecision = cursor.fetchone()[0]

        if reason == 'entry':
            if old_qfl == 'buy':
                price_level = round(old_base - old_base * (H_L_PERCENT / 100), pricePrecision)
                if (current_price < price_level < last_cycle_price) or (last_cycle_price < price_level < current_price):
                    MIDAS_ALLOWS = True

            else:
                price_level = round(old_base + old_base * (H_L_PERCENT / 100), pricePrecision)
                if (current_price < price_level < last_cycle_price) or (last_cycle_price < price_level < current_price):
                    MIDAS_ALLOWS = True

        if MIDAS_ALLOWS == True:
            log(market, "%s %s" % ("MIDAS allows", old_qfl))
        #     if reason == 'entry': log("%s %s" % ("MIDAS", LANGUAGES[LANG]["log_stoch_not_allows"]))
        #     if reason == 'avg': log("%s %s" % ("MIDAS", LANGUAGES[LANG]["log_xxx_not_allows_avg"]))
        #     if reason == 'exit': log("%s %s" % ("MIDAS", LANGUAGES[LANG]["log_price_not_allows_exit"]))
        else:
            pass
            #log("%s %s %s %s %s %s %s %s %s" % ("MIDAS", "not allows", old_qfl, 'current_price', current_price, 'price_level', price_level, 'last_cycle_price', last_cycle_price))
        #GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, SIDE, fast_global, slow_global)

        return MIDAS_ALLOWS#, GLOBAL_STOCH_ALLOWS

    def get_ma_cross_answer(market, reason, side, **kwargs):
        current_price = kwargs['current_price']
        ma_1 = kwargs['ma_1']
        ma_2 = kwargs['ma_2']
        ma_1_prev = kwargs['ma_1_prev']
        ma_2_prev = kwargs['ma_2_prev']
        slow_global = kwargs['slow_global']
        fast_global = kwargs['fast_global']

        MA_ALLOWS = False

        if reason == 'entry':
            table = "trend_entry"
           # MA_CROSS_METHOD = ENTRY_MA_CROSS_METHOD
            MA1 = str(ENTRY_MA_CROSS_MA1)
            MA2 = str(ENTRY_MA_CROSS_MA2)
        if reason == 'avg':
            table = "trend_avg"
            #MA_CROSS_METHOD = AVG_MA_CROSS_METHOD
            MA1 = str(AVG_MA_CROSS_MA1)
            MA2 = str(AVG_MA_CROSS_MA2)
        if reason == 'exit':
            table = "trend_exit"
            #MA_CROSS_METHOD = EXIT_MA_CROSS_METHOD
            MA1 = str(EXIT_MA_CROSS_MA1)
            MA2 = str(EXIT_MA_CROSS_MA2)

        log(market, "%s %s, %s: %.8f, %.8f. %s: %.8f, %.8f" % (
        LANGUAGES[LANG]["log_current_xxx"], 'MA' + MA1, 'MA' + MA2, ma_1, ma_2, LANGUAGES[LANG]["log_previous_xxx"],
        ma_1_prev, ma_2_prev))

        if (side == "buy" and ma_1 > ma_2 and ma_1_prev < ma_2_prev) or (side == "sell" and ma_1 < ma_2 and ma_1_prev > ma_2_prev):
            MA_ALLOWS = True

        else:
            if reason == 'entry': log(market, "%s %s" % ("MA_CROSS", LANGUAGES[LANG]["log_stoch_not_allows"]))
            if reason == 'avg': log(market, "%s %s" % ("MA_CROSS", LANGUAGES[LANG]["log_xxx_not_allows_avg"]))
            if reason == 'exit': log(market, "%s %s" % ("MA_CROSS", LANGUAGES[LANG]["log_price_not_allows_exit"]))

        GLOBAL_STOCH_ALLOWS = get_global_stoch_answer(reason, side, fast_global, slow_global)

        return MA_ALLOWS, GLOBAL_STOCH_ALLOWS


    def create_tables():
        cursor.execute(
            """create table if not exists orders (order_id TEXT, order_side TEXT, market TEXT, order_created DATETIME, order_filled DATETIME, order_cancelled DATETIME, order_price REAL, order_amount REAL, order_cost REAL, order_fee REAL, order_strategy TEXT, squeeze INTEGER, stop_loss INTEGER, deal_number INTEGER, balance REAL, profit REAL);""")
        cursor.execute(
            """CREATE table IF NOT EXISTS counters (counter_market TEXT UNIQUE, counter_count INTEGER DEFAULT 0, orders_total INTEGER);""")
        cursor.execute(
            """CREATE table IF NOT EXISTS trend_entry (market TEXT UNIQUE, trend TEXT, flag TEXT, ask_price REAL, bid_price REAL, macdhist_1 REAL, macdhist_2 REAL, macdhist_3 REAL, macdhist_4 REAL, fast_stoch REAL, slow_stoch REAL, cci REAL, ema200 REAL, rsi REAL, smarsi REAL, atr REAL, efi REAL, ma_1 REAL, ma_2 REAL, upper REAL, middle REAL, lower REAL, fast_global REAL, slow_global REAL, qfl_result INTEGER, qfl_base REAL);""")
        cursor.execute(
            """CREATE table IF NOT EXISTS trend_avg (market TEXT UNIQUE, trend TEXT, flag TEXT, ask_price REAL, bid_price REAL, macdhist_1 REAL, macdhist_2 REAL, macdhist_3 REAL, macdhist_4 REAL, fast_stoch REAL, slow_stoch REAL, cci REAL, ema200 REAL, rsi REAL, smarsi REAL, atr REAL, efi REAL, ma_1 REAL, ma_2 REAL, upper REAL, middle REAL, lower REAL, fast_global REAL, slow_global REAL, qfl_result INTEGER, qfl_base REAL);""")
        cursor.execute(
            """CREATE table IF NOT EXISTS trend_exit (market TEXT UNIQUE, trend TEXT, flag TEXT, ask_price REAL, bid_price REAL, macdhist_1 REAL, macdhist_2 REAL, macdhist_3 REAL, macdhist_4 REAL, fast_stoch REAL, slow_stoch REAL, cci REAL, ema200 REAL, rsi REAL, smarsi REAL, atr REAL, efi REAL, ma_1 REAL, ma_2 REAL, upper REAL, middle REAL, lower REAL, fast_global REAL, slow_global REAL, qfl_result INTEGER, qfl_base REAL);""")
        cursor.execute(
            """CREATE table IF NOT EXISTS timeframe (market TEXT UNIQUE, timeframe_switch INTEGER, initial_tf TEXT, initial_stoch_long INTEGER, initial_stoch_short INTEGER, ema_reason INTEGER, order_count_reason INTEGER, candle_count_reason INTEGER, stoch_reason INTEGER);""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS bo_order_check (market TEXT, checked_date DATETIME)""")
        cursor.execute(
            """CREATE table IF NOT EXISTS limits (market TEXT, amount_precision INTEGER, price_precision INTEGER, amount_limit REAL);""")


    async def record_order(market, id, reason, pnl, balance, immediate):

        try:
            response = await connector.get_order(id, market, reason)
            await asyncio.sleep(2)
        except Exception as e:
            r = False#log(market, '%s: %s %s' % ('GET_ORDER ERROR attempt 1', type(e).__name__, str(e)))

            try:
                response = await connector.get_order(id, market, reason)
                await asyncio.sleep(4)
            except Exception as e:
                log(market, '%s: %s %s' % ('GET_ORDER ERROR attempt 2', type(e).__name__, str(e)))

                try:
                    response = await connector.get_order(id, market, reason)
                    await asyncio.sleep(8)
                except Exception as e:
                    log(market, '%s: %s %s' % ('GET_ORDER ERROR attempt 3', type(e).__name__, str(e)))

        # cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % market)
        # precisions = cursor.fetchall()[0]
        # amountPrecision, pricePrecision, amountLimit = precisions

        if reason == 'entry' and if_not_filled_buy(market, response['side']) == None:  # Если вход и нет открытых ордеров
            deal_number = get_deal_number(market) + 1
        else:
            deal_number = get_deal_number(market)


        if reason == 'entry' or reason == 'avg':
            if response['side'] == 'buy':
                algo = 'LONG'
            else:
                algo = 'SHORT'
        else:
            algo = get_algo(market, deal_number)

        if reason == 'take_profit' and EXIT_METHOD == 'indicators_exit':
            squeeze = 1
            cost = response['amount'] * response['price']
            #print(cost)
        else:
            squeeze = 0
            cost = response['cost']

        if reason == 'stop_loss':
            stop_loss = 1
            if pnl == 'buy':
                algo = 'SHORT'
            else:
                algo = 'LONG'
            pnl = 0
        else:
            stop_loss = 0

        try:
            cursor.execute(
                """
                INSERT INTO orders(order_id, order_side, market, order_created, order_price, order_amount, order_cost, order_fee, order_strategy, squeeze, stop_loss, deal_number, balance, profit) 
                Values (:order_id, :order_side, :market, datetime(), :order_price, :order_amount, :order_cost, :order_fee, :order_strategy, :squeeze, :stop_loss, :deal_number, :balance, :profit)
                """, {'order_id': response['id'],
                      'order_side': response['side'],
                      'market': market,
                      'order_price': response['price'],
                      'order_amount': response['amount'],
                      'order_cost': cost,
                      'order_fee': response['fee'],
                      'order_strategy': algo,
                      'squeeze': squeeze,
                      'stop_loss': stop_loss,
                      'deal_number': deal_number,
                      'balance': balance,
                      'profit': pnl if pnl else 0})

            conn.commit()
        except Exception as e:
            log(market, '%s: %s %s' % ('SQLITE ERROR 05', type(e).__name__, str(e)))
        finally:
            if reason == 'market':
                log(market,
                    '%s %s %s %s' % ('Выставлен рыночный ордер объемом', response['amount'], 'и закрыт по цене', response['price']))
            if reason == 'take_profit':
                log(market, '%s %s %s %s' % ('Выставлен ТП объемом', response['amount'], 'по цене', response['price']))


    async def create_limit(market, side, global_strategy, immediate, price_level, remaining_amount, reason):
        b_pair = market.split('/')[0]
        q_pair = market.split('/')[1]

        q = await connector.get_balance(b_pair, q_pair, config)

        pnl = 0
        if len(q) > 1:
            pnl = q['pnl']

        balance = float(q['balance'])

        cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % market)
        precisions = cursor.fetchall()[0]
        amountPrecision, pricePrecision, amountLimit = precisions

        ORDERS_TOTAL = get_orders_total(market)
        sell_count = get_sell_counter(market)

        # for i, item in enumerate(MARKETS):
        #     if market == item:
        #         LEVERAGE = int(LEVERAGE_ARRAY[i])
        LEVERAGE = float(config.get_value("bot", "leverage"))
        if reason == 'entry':
            margin_mode = config.get_value("bot", "margin_mode")
            try:
                await connector.set_margin_mode(market, margin_mode, LEVERAGE)
                await connector.change_leverage(market, LEVERAGE)
            except Exception as e:
                m = True


        MARTINGALE = config.get_value("bot", "martingale")

        if PERCENT_OR_AMOUNT == True:
            depo_percent = config.get_value("bot", "depo")
            CAN_SPEND = LEVERAGE * (balance * (depo_percent / len(MARKETS)) / 100)
            BO_AMOUNT = CAN_SPEND * config.get_value("bot", "bo_amount") / 100
            SO_AMOUNT = CAN_SPEND - BO_AMOUNT
        else:
            CAN_SPEND = LEVERAGE * config.get_value("bot", "depo") / len(MARKETS)
            BO_AMOUNT = LEVERAGE * config.get_value("bot", "bo_amount")
            SO_AMOUNT = CAN_SPEND - BO_AMOUNT

        p = []
        canspend_so = []
        amount = []
        response = []

        STEP_ONE = float(config.get_value("bot", "first_step"))

        if reason == 'entry':
            deal_number = get_deal_number(market) + 1
            price_level_0 = price_level
            if AVG_PRESET == "MIDAS":
                H_L_PERCENT = ENTRY_H_L_PERCENT
            else:
                H_L_PERCENT = 0
        else:
            deal_number = get_deal_number(market)
            price_level_0 = get_base_order_price(market, side, deal_number)
            if AVG_PRESET == "MIDAS":
                H_L_PERCENT = AVG_H_L_PERCENT
            else:
                H_L_PERCENT = 0

        if reason == 'entry':
            if side == 'buy':
                price_0 = price_level_0 - (price_level_0 * ((STEP_ONE + H_L_PERCENT) / 100))
            else:
                price_0 = price_level_0 + (price_level_0 * ((STEP_ONE + H_L_PERCENT) / 100))
        else:
            price_0 = price_level_0

        if side == 'buy':
            price_1 = price_0 - price_0 * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
        else:
            price_1 = price_0 + price_0 * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
        p_1 = price_1

        for i in range(3, ORDERS_TOTAL + 1):
            if side == 'buy':
                a = price_1 - price_1 * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** i) / 100
            else:
                a = price_1 + price_1 * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** i) / 100
            price_1 = a
            p.append(a)

        if side == 'buy':
            anti_side = 'sell'
        else:
            anti_side = 'buy'

        price = [price_0] + [p_1] + p
        #print('price =', price)

        canspend_0 = BO_AMOUNT
        if MARTINGALE != 1:
            if ORDERS_TOTAL > 1:
                canspend_1 = SO_AMOUNT / ((1 - MARTINGALE ** (ORDERS_TOTAL - 1)) / (1 - MARTINGALE))

        else:
            if ORDERS_TOTAL > 1:
                canspend_1 = SO_AMOUNT / (ORDERS_TOTAL - 1)

        if ORDERS_TOTAL > 1:
            c_1 = canspend_1

            for i in range(3, ORDERS_TOTAL+1):
                c = canspend_1 * MARTINGALE
                canspend_1 = c
                canspend_so.append(c)
            canspend = [canspend_0] + [c_1] + canspend_so
        else:
            canspend = [BO_AMOUNT]
            price = [price_0]
        #print('canspend =', canspend)
        #print(canspend[0] / price[0])

        for i in range(len(price)):
            # if EXCHANGE == 'kucoinfutures':
            #     amount.append(round((canspend[i] / price[i]) / amountLimit, amountPrecision))
            # else:
            amount.append(round(canspend[i] / price[i], amountPrecision))
        if amount[0] < amountLimit:
            amount[0] = amountLimit

        #print('amount =', amount)

        if reason == 'entry':
            if immediate:
                response = await connector.post_market_order(market, side, abs(amount[0]), LEVERAGE, reason)
                #print(response)
                if response:
                    if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
                        await asyncio.sleep(2)
                    await record_order(market, response['id'], reason, pnl, balance, immediate)
            else:
                if ACTIVE_ORDERS == 0:

                    response = await connector.post_limit_order(market, side, abs(amount[0]), price[0], LEVERAGE)
                    if response:
                        if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
                            await asyncio.sleep(4)
                        await record_order(market, response['id'], reason, pnl, balance, immediate)
                else:
                    for i in range(ACTIVE_ORDERS):
                        response = await connector.post_limit_order(market, side, abs(amount[i]), price[i], LEVERAGE)
                        if response:
                            if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
                                await asyncio.sleep(2)
                            await record_order(market, response['id'], reason, pnl, balance, immediate)

        open_orders = open_orders_count(market, side)

        if reason == 'avg':
            if immediate:
                last_order_cost = get_cost_last(market, side)
                am = round(last_order_cost * MARTINGALE / price_level, amountPrecision)

                response = await connector.post_market_order(market, side, am, LEVERAGE, reason)
                if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
                    await asyncio.sleep(2)
                if response:
                    await record_order(market, response['id'], reason, pnl, balance, immediate)
                    log(market, 'Выставлен', sell_count+1, side, 'из', ORDERS_TOTAL, 'объемом', am, 'по цене', round(price_level, pricePrecision))

            else:
                if ORDERS_TOTAL - sell_count == 1:
                    print('ПЫТАЕМСЯ ВЫСТАВИТЬ ПОСЛЕДНЕЕ УСРЕДНЕНИЕ')
                    response = await connector.post_limit_order(market, side, abs(amount[-1]), price[-1], LEVERAGE)
                    if response:
                        await record_order(market, response['id'], reason, pnl, balance, immediate)
                        log(market, 'Выставлен последний', side, 'объемом', amount[-1], 'по цене', price[-1])
                else:#  ACT = 3  open=2  count: 3  12      5   3+3
                    if ACTIVE_ORDERS < ORDERS_TOTAL:
                        for i in range(sell_count+open_orders, sell_count+ACTIVE_ORDERS):
                            print('ПЫТАЕМСЯ ВЫСТАВИТЬ АКТИВНЫЕ ОРДЕРЫ', sell_count+1, sell_count+ACTIVE_ORDERS-open_orders, i)
                            response = await connector.post_limit_order(market, side, abs(amount[i]), price[i], LEVERAGE)
                            if response:
                                await record_order(market, response['id'], reason, pnl, balance, immediate)
                                log(market, 'Выставлен', i+1, side, 'из', ORDERS_TOTAL, 'объемом', amount[i], 'по цене', price[i])

        if reason == 'stop_loss':
            response = await connector.post_stop_loss_order(market, side, remaining_amount, price_level, LEVERAGE)
            if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
                await asyncio.sleep(2)
            if response:
                await record_order(market, response['id'], reason, side, balance, 0)
                log(market, 'Выставлен STOP-LOSS', 'объемом', remaining_amount, 'по цене', round(price_level, pricePrecision))

    async def create_market(market, side, global_strategy, remaining_amount, reason):
        if reason == 'entry':
            deal_number = get_deal_number(market) + 1
        else:
            deal_number = get_deal_number(market)

        b_pair = market.split('/')[0]
        q_pair = market.split('/')[1]

        # for i, item in enumerate(MARKETS):
        #     if market == item:
        #         LEVERAGE = int(LEVERAGE_ARRAY[i])
        LEVERAGE = float(config.get_value("bot", "leverage"))
        if reason == 'entry':
            margin_mode = config.get_value("bot", "margin_mode")
            try:
                await connector.set_margin_mode(market, margin_mode, LEVERAGE)
                await connector.change_leverage(market, LEVERAGE)
            except Exception as e:
                m = True

        try:
            response = await connector.post_market_order(market, side, remaining_amount, LEVERAGE, reason)
        except Exception as e:
            log(market, '%s: %s %s' % ('ORDER_PLACEMENT ERROR 06', type(e).__name__, str(e)))
            if USE_TELEGRAM:
                try:
                    send_msg("{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⚠ ' + 'CREATE MARKET ORDER ERROR 06 ' + type(e).__name__ + str(e)))
                except Exception as e:
                    log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))



        if EXCHANGE == 'bybit' or EXCHANGE == 'bingx':
            await asyncio.sleep(2)

        q = await connector.get_balance(b_pair, q_pair, config)
        pnl = 0
        if len(q) > 1:
            pnl = q['pnl']
        balance = float(q['balance'])

        if response:
            #print(response['id'])
            await record_order(market, response['id'], 'market', pnl, balance, 1)

    async def create_take_profit(market, side, global_strategy, immediate, amount, price_level):
        global back
        back = 1

        # for i, item in enumerate(MARKETS):
        #     if market == item:
        #         LEVERAGE = int(LEVERAGE_ARRAY[i])

        # margin_mode = config.get_value("bot", "margin_mode")
        LEVERAGE = float(config.get_value("bot", "leverage"))
        # try:
        #     await connector.set_margin_mode(market, margin_mode, LEVERAGE)
        #     await connector.change_leverage(market, LEVERAGE)
        # except Exception as e:
        #     m = True

        #response = None
        try:
            if immediate:
                response = await connector.post_market_order(market, side, amount, LEVERAGE, 'take_profit')
            else:
                response = await connector.post_limit_order(market, side, amount, price_level, LEVERAGE)

        except Exception as e:
            log(market, '%s: %s %s' % ('ORDER_PLACEMENT ERROR 05', type(e).__name__, str(e)))


        if response:
            #print(response)
            await record_order(market, response['id'], 'take_profit', 0, 0, 0)
            increment_sell_counter(market)

            if ACTIVE_ORDERS == 0:
                cursor.execute("""INSERT OR REPLACE INTO trend_avg(flag, ask_price, bid_price, market) values(:flag, :ask_price, :bid_price, :market)""", {'flag': '0', 'ask_price': price_level, 'bid_price': price_level, 'market': market})
                conn.commit()

        if TIMEFRAME_SWITCHING:
            U_TIMEFRAME = config.get_value("averaging", "timeframe").replace(' ', '').split(',')[0]
            U_STOCH_LONG_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_long_up_level")
            U_STOCH_SHORT_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_short_low_level")
            record_timeframe(market=market, timeframe_switch=0, initial_tf=U_TIMEFRAME, initial_stoch_long=U_STOCH_LONG_LEVEL, initial_stoch_short=U_STOCH_SHORT_LEVEL, ema_reason=0, order_count_reason=0, candle_count_reason=0, stoch_reason=0)

    async def bot(thread, state):

        if not thread.stopped():

            try:
                GLOBAL_TF = config.get_value("indicators_tuning", "global_timeframe")
                TIME_SLEEP = config.get_value("bot", "time_sleep")
                TIME_SLEEP_KOEFF = config.get_value("bot", "time_sleep_coeff")
                date = datetime.now()
                ORDERS_TOTAL = get_orders_total(MARKETS[0])
                AVG_PRESET = config.get_value('averaging', 'avg_preset')
                ENTRY_PRESET = config.get_value('entry', 'entry_preset')
                EXIT_PRESET = config.get_value('exit', 'exit_preset')
                ENTRY_TF = config.get_value('entry', 'entry_timeframe')
                EXIT_TF = config.get_value('exit', 'exit_timeframe')



                for market in MARKETS:
                    log("------------------------------------------------------------------------------------------------")
                    b_pair = market.split('/')[0]
                    q_pair = market.split('/')[1]
                    amountPrecision = None

                    try:
                        await connector.configure(config, market)
                    except Exception as e:
                        log(market, '%s: %s %s' % ('CONFIGURE ERROR 01', type(e).__name__, str(e)))

                    try:
                        if count('bot', 'limits', market) == None or int(count('bot', 'limits', market)[0]) < 1:
                            amountPrecision, pricePrecision, amountLimit = connector.get_precision(market)
                            cursor.execute("""INSERT INTO limits(market, amount_precision, price_precision, amount_limit) values(:market, :amount_precision, :price_precision, :amount_limit)""",
                                {'market': market, 'amount_precision': amountPrecision, 'price_precision': pricePrecision, 'amount_limit': amountLimit})
                            conn.commit()
                        else:
                            cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % market)
                            precisions = cursor.fetchall()[0]
                            amountPrecision, pricePrecision, amountLimit = precisions
                    except Exception as e:
                        g = True


                    if TIMEFRAME_SWITCHING == True:
                        AVG_TF = get_initial_tf(market)
                    else:
                        AVG_TF = config.get_value("averaging", "timeframe")

                    if amountPrecision == None:
                        return

                    # qqq = await connector.get_order('1493489368169992192','XRP/USDT', 'market')
                    # print(qqq)
                    # margin_mode = config.get_value("bot", "margin_mode")
                    # LEVERAGE = float(config.get_value("bot", "leverage"))
                    # await connector.set_margin_mode('XRP/USDT', margin_mode, LEVERAGE)
                    # await connector.get_my_trades('1000FLOKI/USDT')
                    # await asyncio.sleep(12130)

                    try:
                        q = await connector.get_balance(b_pair, q_pair, config)# Берем данные по позе: balance, pnl, pos_average, leverage, pos_amount, pos_cost, pos_id, roe_pcnt
                    except Exception as e:
                        pass
                        await asyncio.sleep(1)
                        try:
                            q = await connector.get_balance(b_pair, q_pair, config)
                        except Exception as e:
                            log(market, '%s: %s' % ('GET BALANCE ERROR 01', str(e)))

                    balance = float(q['balance'])

                    if len(q) > 1:
                        pnl = q['pnl']
                        pos_average = q['pos_average']
                        pos_amount = abs(q['pos_amount'])
                        pos_cost = q['pos_cost']
                        roe_pcnt = q['roe_pcnt']
                        leverage = q['leverage']
                        liquidation = q['liquidation']
                        free = q['free']
                        if q['side'] == 'long':
                            side = 'buy'
                        else:
                            side = 'sell'
                    else:
                        pnl = 0
                        pos_average = 0
                        pos_amount = 0
                        pos_cost = 0
                        roe_pcnt = 0
                        leverage = 0
                        liquidation = 0
                        free = balance
                        #side = None

                    sell_count = get_sell_counter(market)

                    if count('bot', 'orders', market) == None:
                        c = 0
                    else:
                        c = int(count('bot', 'orders', market)[0])

                    d_n = get_deal_number(market)
                    #print('d_n',d_n)
                    if d_n:
                        get_base_order = get_base_order_state(market, d_n)
                        algo = get_algo(market, d_n)
                    else:
                        get_base_order = 0
                        #print('get_base_order = 0')
                        algo = None

                    if algo:
                        if algo == 'LONG':
                            not_filled_buy = if_not_filled_buy(market, 'sell')
                        else:
                            not_filled_buy = if_not_filled_buy(market, 'buy')
                    else:
                        not_filled_buy = None

                    #print('algo', algo)
                    if algo:
                        n_filled_orders_q = """SELECT order_id FROM orders WHERE market='%s' AND order_filled IS NULL AND order_cancelled IS NULL""" % (market)
                        cursor.execute(n_filled_orders_q)
                        n_filled_orders = cursor.fetchone()
                    else:
                        n_filled_orders = None

                    ask, bid = await connector.get_ask_bid(market)
                    #print(ask, bid)
                    if EXCHANGE == 'binance':
                        current_ask = ask
                        current_bid = current_ask
                    else:
                        current_ask = ask
                        current_bid = bid


                    #(Если обнаружена поза и БД пуста) или (БД не пуста, есть поза и нет выставленного БО)
                    if (c < 1 and len(q) > 1) or (c > 0 and len(q) > 1 and sell_count < 1 and get_base_order == 0):
                        global_ind = await get_indicators_advice(config, market, GLOBAL_TF, 'avg')
                        current_price = global_ind['close_1']
                        fast_global = global_ind['fast']
                        slow_global = global_ind['slow']
                        global_strategy = global_ind['trend']

                        log(market, '%s %s %s' % (LANGUAGES[LANG]["log_unknown_pos_det"], pos_amount, b_pair))
                        log(market, '%s: %s. %s: %s' % (LANGUAGES[LANG]["log_avr_buy_price_is"], pos_average, LANGUAGES[LANG]["log_current_price"], current_price))
                        log(market, LANGUAGES[LANG]['log_record_pos'])


                        if side == 'buy':
                            order_algo = 'LONG'
                        else:
                            order_algo = 'SHORT'


                        flag = False
                        try:
                            cursor.execute(
                                """
                                INSERT INTO orders(order_id, order_side, market, order_created, order_filled, order_price, order_amount, order_cost, order_fee, order_strategy, deal_number, balance, profit) 
                                Values (:order_id, :order_side, :market, datetime(), datetime(), :order_price, :order_amount, :order_cost, :order_fee, :order_strategy, :deal_number, :balance, :profit)
                                """, {'order_id': 0, 'order_side': side, 'market': market, 'order_price': pos_average, 'order_amount': pos_amount, 'order_cost': pos_cost, 'order_fee': 0, 'order_strategy': order_algo, 'deal_number': get_deal_number(market)+1, 'balance': balance, 'profit': 0})
                            conn.commit()
                        except Exception as e:
                            log(market, '%s: %s %s' % ('SQLITE ERROR 03', type(e).__name__, str(e)))
                        finally:
                            flag = True

                        #Вытавляем ТП в виде сквиз-ордера
                        if flag == True:

                            if EXIT_METHOD == 'profit_exit':
                                if side == 'buy':
                                    price_level = round(pos_average + pos_average * EXIT_PROFIT_LEVEL / 100, pricePrecision)
                                else:
                                    price_level = round(pos_average - pos_average * EXIT_PROFIT_LEVEL / 100, pricePrecision)
                            else:
                                if side == 'buy':
                                    price_level = round(pos_average + pos_average * SQUEEZE_PROFIT / 100, pricePrecision)
                                else:
                                    price_level = round(pos_average - pos_average * SQUEEZE_PROFIT / 100, pricePrecision)

                            try:
                                #print('market=',market)
                                await create_take_profit(market=market, side='sell' if side == 'buy' else 'buy', global_strategy=global_strategy, immediate=0, amount=abs(pos_amount), price_level=price_level)
                            except Exception as e:
                                log(market, '%s: %s %s' % ('TAKE PROFIT PLACEMENT ERROR 01', type(e).__name__, str(e)))
                                if USE_TELEGRAM:
                                    try:
                                        send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'TAKE PROFIT PLACEMENT ERROR 01' + type(e).__name__ + str(e)))
                                    except Exception as e:
                                        log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                state["needed_stop"] = True
                                state["fixed_profit"] = True
                                await asyncio.sleep(0.1)
                                return

                            if count('bot', 'orders', market) == None:
                                c = 0
                            else:
                                c = int(count('bot', 'orders', market)[0])

                            d_n = get_deal_number(market)
                            #print('d_n', d_n)
                            if d_n:
                                get_base_order = get_base_order_state(market, d_n)
                                algo = get_algo(market, d_n)
                            else:
                                get_base_order = 0
                                #print('get_base_order = 0')
                                algo = None

                            if algo:
                                if algo == 'LONG':
                                    not_filled_buy = if_not_filled_buy(market, 'sell')
                                else:
                                    not_filled_buy = if_not_filled_buy(market, 'buy')
                            else:
                                not_filled_buy = None

                            if EXCHANGE == 'bybit':
                                await asyncio.sleep(1)

                        break


                    # ЛОГИКА ВХОДА
                    if len(q) == 1 and sell_count < 1 and (not n_filled_orders):#или нет незакрытых фиксов
                        if TIMEFRAME_SWITCHING:
                            U_TIMEFRAME = config.get_value("averaging", "timeframe").replace(' ', '').split(',')[0]
                            U_STOCH_LONG_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_long_up_level")
                            U_STOCH_SHORT_LEVEL = config.get_value("avg_preset_stoch_cci", "stoch_short_low_level")
                            record_timeframe(market=market, timeframe_switch=0, initial_tf=U_TIMEFRAME, initial_stoch_long=U_STOCH_LONG_LEVEL, initial_stoch_short=U_STOCH_SHORT_LEVEL, ema_reason=0, order_count_reason=0, candle_count_reason=0, stoch_reason=0)


                        global_ind = await get_indicators_advice(config, market, GLOBAL_TF, 'entry')
                        ind = await get_indicators_advice(config, market, ENTRY_TF, 'entry')
                        fast_global = global_ind['fast']
                        slow_global = global_ind['slow']

                        global_strategy = global_ind['trend']

                        ff = False
                        if ENTRY_BY_INDICATORS == True:
                            #if time.time() - start_time < 25:
                            if ENTRY_CCI_CROSS_USE_PRICE == True and ENTRY_PRESET == "CCI_CROSS":
                                add_text = " + price"
                            else:
                                add_text = ""

                            log(market, LANGUAGES[LANG]["log_entry_preset_chosen"], ENTRY_PRESET+add_text, '('+ENTRY_TF+'),', LANGUAGES[LANG]["log_free_balance"], balance, q_pair)
                            log(market, LANGUAGES[LANG]["log_no_position"])
                            log(market, "%s (%s): %s" % ("GLOBAL TREND", GLOBAL_TF, global_strategy))

                            if ENTRY_PRESET == 'STOCH_CCI':

                                #log('LONG', ind['fast'] ,ENTRY_STOCH_C_LONG_UP_LEVEL, ENTRY_STOCH_C_LONG_LOW_LEVEL, ind['cci_3'], ind['cci_2'], ind['cci_1'], ENTRY_CCI_LONG_LEVEL)
                                #log('SHORT', ind['fast'] ,ENTRY_STOCH_C_SHORT_UP_LEVEL, ENTRY_STOCH_C_SHORT_LOW_LEVEL, ind['cci_3'], ind['cci_2'], ind['cci_1'], ENTRY_CCI_SHORT_LEVEL)
                                if ind['cci_1'] < ENTRY_CCI_LONG_LEVEL and ENTRY_STOCH_C_LONG_UP_LEVEL > ind['fast'] > ENTRY_STOCH_C_LONG_LOW_LEVEL:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask
                                elif ind['cci_1'] > ENTRY_CCI_SHORT_LEVEL and ENTRY_STOCH_C_SHORT_UP_LEVEL > ind['fast'] > ENTRY_STOCH_C_SHORT_LOW_LEVEL:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid
                                else:
                                    entry_side = None
                                    log(market, LANGUAGES[LANG]["log_no_conditions"])

                                #print('entry_side', entry_side)
                                if entry_side != None:
                                    STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_cci_answer(market, 'entry', entry_side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], cci_3=ind['cci_3'], cci_2=ind['cci_2'], cci=ind['cci_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                    if ENTRY_USE_STOCH_C == True:

                                        if STOCH_ALLOWS == True:
                                            log(market, "%s %s: %s %s: %0.3f, %s %s: %0.3f" % (LANGUAGES[LANG]["log_stoch_allows"], text_stoch,
                                            LANGUAGES[LANG]["fast_STOCH"], ENTRY_TF, ind['fast'],
                                            LANGUAGES[LANG]["slow_STOCH"], ENTRY_TF, ind['slow']))
                                        if STOCH_ALLOWS == False:
                                            log(market, "%s %s. %s %s: %0.3f, %s %s: %0.3f" % (
                                            text_stoch, LANGUAGES[LANG]["log_stoch_not_allows"],
                                            LANGUAGES[LANG]["fast_STOCH"], ENTRY_TF, ind['fast'],
                                            LANGUAGES[LANG]["slow_STOCH"], ENTRY_TF, ind['slow']))
                                    if ENTRY_USE_CCI == True:
                                        if CCI_ALLOWS == True:
                                            log(market, "%s %s. %s (%s): (%0.3f, %0.3f, %0.3f)" % (
                                            LANGUAGES[LANG]["log_cci_allows"], entry_algo, 'CCI',
                                            ENTRY_TF, round(ind['cci_3'], pricePrecision), round(ind['cci_2'], pricePrecision), round(ind['cci_1'], pricePrecision)))
                                        if CCI_ALLOWS == False:
                                            log(market, "%s. %s %s: (%0.3f, %0.3f, %0.3f)" % (
                                            LANGUAGES[LANG]["log_cci_not_allows"], 'CCI', ENTRY_TF, round(ind['cci_3'], pricePrecision), round(ind['cci_2'], pricePrecision), round(ind['cci_1'], pricePrecision)))
                                    if USE_GLOBAL_STOCH == True:
                                        log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))

                                    if GLOBAL_STOCH_ALLOWS and STOCH_ALLOWS and CCI_ALLOWS:
                                        ff = True

                            if ENTRY_PRESET == 'STOCH_RSI':
                                if ind['rsi_1'] < ENTRY_RSI_LONG_LEVEL and ENTRY_STOCH_S_LONG_UP_LEVEL > ind['fast'] > ENTRY_STOCH_S_LONG_LOW_LEVEL:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask
                                elif ind['rsi_1'] > ENTRY_RSI_SHORT_LEVEL and ENTRY_STOCH_S_SHORT_UP_LEVEL > ind['fast'] > ENTRY_STOCH_S_SHORT_LOW_LEVEL:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid
                                else:
                                    entry_side = None
                                    log(market, LANGUAGES[LANG]["log_no_conditions"])

                                if entry_side != None:
                                    STOCH_ALLOWS, RSI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_rsi_answer(market, 'entry', entry_side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], rsi_3=ind['rsi_3'], rsi_2=ind['rsi_2'], rsi=ind['rsi_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                    if ENTRY_USE_STOCH_S == True:

                                        if STOCH_ALLOWS == True:
                                            log(market, "%s %s: %s %s: %0.3f, %s %s: %0.3f" % (LANGUAGES[LANG]["log_stoch_allows"], text_stoch,
                                            LANGUAGES[LANG]["fast_STOCH"], ENTRY_TF, ind['fast'],
                                            LANGUAGES[LANG]["slow_STOCH"], ENTRY_TF, ind['slow']))
                                        if STOCH_ALLOWS == False:
                                            log(market, "%s %s. %s %s: %0.3f, %s %s: %0.3f" % (
                                            text_stoch, LANGUAGES[LANG]["log_stoch_not_allows"],
                                            LANGUAGES[LANG]["fast_STOCH"], ENTRY_TF, ind['fast'],
                                            LANGUAGES[LANG]["slow_STOCH"], ENTRY_TF, ind['slow']))
                                    if ENTRY_USE_RSI == True:
                                        if RSI_ALLOWS == True:
                                            log(market, "%s %s. %s (%s): (%0.3f, %0.3f, %0.3f)" % (
                                            LANGUAGES[LANG]["log_rsi_allows"], entry_algo, 'RSI',
                                            ENTRY_TF, round(ind['rsi_3'], pricePrecision), round(ind['rsi_2'], pricePrecision), round(ind['rsi_1'], pricePrecision)))
                                        if RSI_ALLOWS == False:
                                            log(market, "%s. %s %s: (%0.3f, %0.3f, %0.3f)" % (
                                            LANGUAGES[LANG]["log_rsi_not_allows"], 'RSI', ENTRY_TF, round(ind['rsi_3'], pricePrecision), round(ind['rsi_2'], pricePrecision), round(ind['rsi_1'], pricePrecision)))
                                    if USE_GLOBAL_STOCH == True:
                                        log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))

                                    if GLOBAL_STOCH_ALLOWS and STOCH_ALLOWS and RSI_ALLOWS:
                                        ff = True

                            if ENTRY_PRESET == "CCI_CROSS":
                                if ind['cci_1'] < ENTRY_CCI_CROSS_LONG_LEVEL:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask
                                elif ind['cci_1'] > ENTRY_CCI_CROSS_SHORT_LEVEL:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid
                                else:
                                    entry_side = None

                                if entry_side != None:
                                    if USE_GLOBAL_STOCH == True:
                                        log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                    CCI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_cci_cross_answer(market, 'entry', entry_side, current_price=current_price, cci=ind['cci_1'], cci_2=ind['cci_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                    if GLOBAL_STOCH_ALLOWS and CCI_CROSS_ALLOWS:
                                        ff = True

                            if ENTRY_PRESET == "MA_CROSS":
                                ma_1 = ind['ma_1_1']
                                ma_2 = ind['ma_2_1']

                                if ma_1 > ma_2:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask
                                else:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid


                                if entry_side != None:
                                    if USE_GLOBAL_STOCH == True:
                                        log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                    MA_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_ma_cross_answer(market, 'entry', entry_side, current_price=current_price, ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], ma_1_prev=ind['ma_1_2'], ma_2_prev=ind['ma_2_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                    if GLOBAL_STOCH_ALLOWS and MA_CROSS_ALLOWS:
                                        ff = True


                            if ENTRY_PRESET == "RSI_SMARSI":
                                if ind['smarsi'] < ENTRY_SMARSI_CROSS_LONG_UP_LEVEL:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask
                                elif ind['smarsi'] > ENTRY_SMARSI_CROSS_SHORT_LOW_LEVEL:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid
                                else:
                                    entry_side = None

                                if entry_side != None:
                                    if USE_GLOBAL_STOCH == True:
                                        log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                    RSI_SMARSI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_rsi_smarsi_cross_answer(market, 'entry', entry_side, current_price=current_price, rsi=ind['rsi_1'], smarsi=ind['smarsi'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                    if GLOBAL_STOCH_ALLOWS and RSI_SMARSI_CROSS_ALLOWS:
                                        ff = True

                            if ENTRY_PRESET == 'PRICE':
                                if current_ask < ind['close_2'] - ind['close_2'] * ENTRY_PRICE_DELTA_LONG/100:
                                    entry_side = 'buy'
                                    entry_algo = 'LONG'
                                    current_price = current_ask

                                elif current_bid > ind['close_2'] + ind['close_2'] * ENTRY_PRICE_DELTA_SHORT/100:
                                    entry_side = 'sell'
                                    entry_algo = 'SHORT'
                                    current_price = current_bid
                                else:
                                    entry_side = None

                                if entry_side != None:
                                    log(f"{market} PRICE-пересет позволяет войти в {entry_algo}. Цена close {ind['close_2']}, текущая цена {current_price}")
                                    ff = True

                            if ENTRY_PRESET != 'MIDAS':
                                if ff:
                                    log(market, "%s %s. %s %s" % (LANGUAGES[LANG]["log_signal_found"], ENTRY_PRESET, LANGUAGES[LANG]["log_entry_with_algo"], entry_algo))

                                    if ACTIVE_ORDERS == 0 and STEP_ONE < 0.01:
                                        imm = 1
                                    else:
                                        imm = 0

                                    try:
                                        await create_limit(market, entry_side, global_strategy, imm, current_price, 0, 'entry')
                                    except Exception as e:
                                        log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 00', type(e).__name__, str(e)))
                                        if USE_TELEGRAM:
                                            try:
                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 00 ' + type(e).__name__ + str(e)))
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                        state["needed_stop"] = True
                                        state["fixed_profit"] = True
                                        await asyncio.sleep(0.1)
                                        return
                                    finally:
                                        if USE_TELEGRAM:
                                            try:
                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + LANGUAGES[LANG]["log_entry_with_algo"] + ' ' + entry_algo))#, '💰 ' + str(LANGUAGES[LANG]["log_free_balance"]) + ' ' + str(q[0]) + ' ' + str(q_pair)))
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                else:
                                    record_trend(market=market, table="trend_entry", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=0)

                            if ENTRY_PRESET == 'MIDAS':
                                new_qfl = ind['qfl_result']
                                new_base = ind['qfl_base']
                                # берем из БД QFL и базу, если они есть
                                old_qfl_base = """SELECT qfl_result, qfl_base FROM trend_entry WHERE market='%s'""" % (market)
                                cursor.execute(old_qfl_base)
                                result = cursor.fetchall()
                                if not result or result[0] == None:
                                    old_qfl = 0
                                    old_base = 0
                                else:
                                    old_qfl = result[0][0]
                                    old_base = result[0][1]

                                if old_qfl == 'buy':
                                    algo = 'LONG'
                                    current_price = current_ask
                                else:
                                    algo = 'SHORT'
                                    current_price = current_bid
                                # flag = False
                                # old_qfl = 0
                                # old_base = 0
                                # algo = 'SHORT'
                                #new_qfl = 'sell'
                                #new_base = 6.08
                                if new_qfl and not old_qfl:  # если найден новый сигнал QFL и ранее в БД они отсутствовали
                                    #if new_qfl == 'sell':
                                    if (new_qfl == 'buy' and global_ind['fast'] < global_ind['slow']) or (new_qfl == 'sell' and global_ind['fast'] > global_ind['slow']):
                                        #log(market, 'ГЛОБАЛЬНЫЙ ТРЕНД ПОЗВОЛЯЕТ НАЧАТЬ МОНИТОРИНГ ВХОДА В РЫНОК')
                                        log(market, LANGUAGES[LANG]["log_signal_found"], ENTRY_PRESET, new_qfl, LANGUAGES[LANG]["log_with_qfl_base"], new_base)
                                        if ACTIVE_ORDERS > 0:
                                            try:
                                                # запускаем лимитные ордеры
                                                await create_limit(market, new_qfl, global_strategy, 0, new_base, 0, 'entry')
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 01', type(e).__name__, str(e)))
                                                if USE_TELEGRAM:
                                                    try:
                                                        send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 01 ' + type(e).__name__ + str(e)))
                                                    except Exception as e:
                                                        log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                state["needed_stop"] = True
                                                state["fixed_profit"] = True
                                                await asyncio.sleep(0.1)
                                                return
                                            try:
                                                send_msg("{}\n{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + LANGUAGES[LANG]["log_signal_found"] + ' ' + ENTRY_PRESET + ' ' + str(new_qfl), LANGUAGES[LANG]["log_with_qfl_base"] + ' ' + str(new_base)))
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                        # Пишем в БД QFL сигнал и уровень базы
                                        record_trend(market=market, table="trend_entry", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=new_qfl, qfl_base=new_base)


                                if old_qfl and ACTIVE_ORDERS == 0:#Если используем маркет ордеры
                                    MIDAS_ALLOWS = False
                                    #ЛОГИКА ВХОДА ПРИ НАХОЖДЕНИИ ЦЕНЫ ЗА РАМКАМИ БАЗЫ
                                    MIDAS_ALLOWS = get_midas_answer(market=market, reason='entry', current_price=current_price, old_qfl=old_qfl, old_base=old_base)
                                    #MIDAS_ALLOWS = True
                                    if MIDAS_ALLOWS:
                                        price_level = current_price
                                        #print(current_price)
                                        try:
                                            await create_limit(market, old_qfl, global_strategy, 1, price_level, 0, 'entry')
                                        except Exception as e:
                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 02', type(e).__name__, str(e)))
                                            if USE_TELEGRAM:
                                                try:
                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 02 ' + type(e).__name__ + str(e)))
                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                            state["needed_stop"] = True
                                            state["fixed_profit"] = True
                                            await asyncio.sleep(0.1)
                                            return
                                        finally:
                                            log(market, "%s %s %s" % (LANGUAGES[LANG]["log_price_out_of_base"], LANGUAGES[LANG]["log_entry_with_algo"], algo))
                                            try:
                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + LANGUAGES[LANG]["log_entry_with_algo"] + ' ' + algo))#, '💰 ' + str(LANGUAGES[LANG]["log_free_balance"]) + ' ' + str(q[0]) + ' ' + str(q_pair)))
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                    # ЛОГИКА РАЗВОРОТА ПРИ ОБНАРУЖЕНИИ ПРОТИВОПОЛОЖНОГО ПАТТЕРНА
                                    if (old_qfl == 'buy' and current_price > old_base and new_qfl and new_qfl == 'sell' and global_ind['fast'] > global_ind['slow']) or (old_qfl == 'sell' and current_price < old_base and new_qfl and new_qfl == 'buy' and global_ind['fast'] < global_ind['slow']): #если глобальный тренд растущий то переворачиваем в шорт
                                        if old_qfl == 'buy' and new_qfl == 'sell':
                                            algo = 'SHORT'
                                        else:
                                            algo = 'LONG'
                                        log(market, LANGUAGES[LANG]["log_reversal_pattern_found"], algo, LANGUAGES[LANG]["log_with_qfl_base"], new_base)
                                        try:
                                            send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + LANGUAGES[LANG]["log_reversal_pattern_found"] + ' ' + algo + ' ' + LANGUAGES[LANG]["log_with_qfl_base"] + ' ' + str(new_base)))
                                        except Exception as e:
                                            log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                    # if : #если глобальный тренд падающий то переворачиваем в лонг
                                    #     log(market, 'НАЙДЕН РАЗВОРОТНЫЙ ПАТТЕРН. НАЧИНАЕМ МОНИТОРИТЬ ЛОНГ', LANGUAGES[LANG]["log_with_qfl_base"], new_base)
                                    #     try:
                                    #         send_msg("{}\n{}".format('📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + 'НАЙДЕН РАЗВОРОТНЫЙ ПАТТЕРН. НАЧИНАЕМ МОНИТОРИТЬ ЛОНГ ' + LANGUAGES[LANG]["log_with_qfl_base"] + str(new_base)))
                                    #     except Exception as e:
                                    #         log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                    if (old_qfl == 'buy' and current_price > old_base and new_qfl and new_qfl == 'sell' and global_ind['fast'] > global_ind['slow']) or (old_qfl == 'sell' and current_price < old_base and new_qfl and new_qfl == 'buy' and global_ind['fast'] < global_ind['slow']) or (old_qfl == 'buy' and current_price > old_base and new_qfl and new_qfl == 'buy') or (old_qfl == 'sell' and current_price < old_base and new_qfl and new_qfl == 'sell'):
                                        record_trend(market=market, table="trend_entry", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=new_qfl, qfl_base=new_base)
                                        print('Записали данные')
                                        # Пишем в БД QFL сигнал и уровень базы

                                    cursor.execute("""UPDATE trend_entry SET ask_price=:ask_price, bid_price=:bid_price WHERE market=:market""", {'ask_price': current_ask, 'bid_price': current_bid, 'market': market})
                                    conn.commit()
                                    #if flag == True:#Если ввыставили ордер, то обнуляем QFL сигнал и уровень базы
                                        #record_trend(market=market, table="trend_entry", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=0)
                        else:
                            # вход без индикаторов
                            fast_global = global_ind['fast']
                            slow_global = global_ind['slow']

                            if global_strategy == 'LONG':
                                side = 'buy'
                                algo = 'LONG'
                                price_level = current_ask
                            else:
                                side = 'sell'
                                algo = 'SHORT'
                                price_level = current_bid

                            USG = ' по GLOBAL_STOCH' if USE_GLOBAL_STOCH else ' НОНСТОП по глобальному тренду ' + global_strategy
                            log(f'{market} Выбран режим входа{USG}. {LANGUAGES[LANG]["log_free_balance"]} {balance} {q_pair}')
                            log(f'{market} {GLOBAL_TF}, {global_strategy}, EMA200 {global_ind["ema200"]}')

                            GLOBAL_STOCH_ALLOWS = get_global_stoch_answer('entry', side, fast_global, slow_global)
                            if USE_GLOBAL_STOCH and GLOBAL_STOCH_ALLOWS:
                                log(market, "%s: %s %s" % (LANGUAGES[LANG]["log_global_stoch_allows_entry"], LANGUAGES[LANG]["fast_STOCH"], fast_global))
                            if USE_GLOBAL_STOCH and not GLOBAL_STOCH_ALLOWS:
                                log(market, "%s: %s %s" % (LANGUAGES[LANG]["log_global_stoch_not_allows_entry"], LANGUAGES[LANG]["fast_STOCH"], fast_global))

                            if (USE_GLOBAL_STOCH and GLOBAL_STOCH_ALLOWS) or not USE_GLOBAL_STOCH:
                                try:
                                    if ACTIVE_ORDERS == 0 and STEP_ONE < 0.01:
                                        await create_limit(market, side, global_strategy, 1, price_level, 0, 'entry')
                                    else:
                                        await create_limit(market, side, global_strategy, 0, price_level, 0, 'entry')
                                except Exception as e:
                                    log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 08', type(e).__name__, str(e)))
                                    if USE_TELEGRAM:
                                        try:
                                            send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 02 ' + type(e).__name__ + str(e)))
                                        except Exception as e:
                                            log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                    state["needed_stop"] = True
                                    state["fixed_profit"] = True
                                    await asyncio.sleep(0.1)
                                    return
                                finally:
                                    log(market, "%s %s" % ('Размещаем ордеры в соответствии с глобальным трендом', algo))
                                    try:
                                        send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market, '✅ ' + LANGUAGES[LANG]["log_entry_with_algo"] + ' ' + algo))#, '💰 ' + str(LANGUAGES[LANG]["log_free_balance"]) + ' ' + str(q[0]) + ' ' + str(q_pair)))
                                    except Exception as e:
                                        log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                    else:
                        # есть поза или выставлена лимитка
                        global_ind = await get_indicators_advice(config, market, GLOBAL_TF, 'avg')
                        ind = await get_indicators_advice(config, market, AVG_TF, 'avg')  # запрашиваем поиск нового QFL и новой базы
                        fast_global = global_ind['fast']
                        slow_global = global_ind['slow']
                        fast = ind['fast']
                        slow = ind['slow']
                        ema_global = global_ind['ema200']
                        global_strategy = global_ind['trend']
                        stop_loss_price_long = ind['extreme_min'] / 1.01
                        stop_loss_price_short = ind['extreme_max'] * 1.01

                        if (len(q) > 1 and pos_amount > 0) or (n_filled_orders and algo == 'LONG'): #поза long или выставлен базовый ордер long
                            #print('Мониторим усреднение лонга')
                            side = 'buy'
                            algo_logo = '📈'
                            anti_side = 'sell'
                            current_price = current_bid

                        if (len(q) > 1 and pos_amount < 0) or (n_filled_orders and algo == 'SHORT'): #поза short или выставлен базовый ордер short
                            #print('Мониторим усреднение шорта')
                            side = 'sell'
                            algo_logo = '📉'
                            anti_side = 'buy'
                            current_price = current_ask


                        if len(q) > 1:
                            log(market, "%s %s %s %s %s. %s %s (%s %s)" % (LANGUAGES[LANG]["log_we_have_pos"], algo, LANGUAGES[LANG]["log_with_amount"], pos_amount, b_pair, LANGUAGES[LANG]["average_price_delta"], roe_pcnt, pnl, q_pair))
                        else:
                            log(market, LANGUAGES[LANG]["log_check_orders"])


                        if ACTIVE_ORDERS == 0:
                            orders_q = """
                                 SELECT
                                   o.order_id, o.order_side, o.order_price, o.order_amount, o.order_filled, o.order_cancelled, o.order_created, o.squeeze, o.stop_loss, o.deal_number
                                 FROM
                                   orders o
                                 WHERE
                                      o.market='%s' 
                                      AND ((o.order_side = '%s' and o.order_filled IS NULL) OR (o.order_side = '%s' AND order_filled IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orders)) OR (o.order_side = '%s' and o.order_filled IS NULL)) 
                                      AND o.order_cancelled IS NULL
                                      AND o.deal_number='%s'
                                 ORDER BY order_created DESC
                            """ % (market, side, side, anti_side, get_deal_number(market))
                        else:
                            orders_q = """
                                 SELECT
                                   o.order_id, o.order_side, o.order_price, o.order_amount, o.order_filled, o.order_cancelled, o.order_created, o.squeeze, o.stop_loss, o.deal_number
                                 FROM
                                   orders o
                                 WHERE
                                      o.market='%s' 
                                      AND ((o.order_side = '%s' and o.order_filled IS NULL) OR (o.order_side = '%s' AND order_filled IS NOT NULL AND NOT EXISTS (SELECT 1 FROM orders)) OR (o.order_side = '%s' and o.order_filled IS NULL)) 
                                      AND o.order_cancelled IS NULL
                                      AND o.deal_number='%s'
                                 ORDER BY order_created ASC
                            """ % (market, side, side, anti_side, get_deal_number(market))

                        orders_info = {}
                        for row in cursor.execute(orders_q):
                            orders_info[str(row[0])] = {'order_id': row[0], 'order_side': row[1], 'order_price': row[2], 'order_amount': row[3], 'order_filled': row[4], 'order_cancelled': row[5], 'order_created': row[6], 'squeeze': row[7], 'stop_loss': row[8], 'deal_number': row[9]}

                        if orders_info:
                            if not_filled_buy != None and sell_count == 0:
                                if ACTIVE_ORDERS == 0 and pnl < 0:
                                    last_order_cost = get_cost_last(market, side)
                                    next_avr_cost = round((last_order_cost / leverage) * MARTINGALE, amountPrecision)

                                    #if ORDERS_TOTAL > 1:
                                    log(market, "%s" % LANGUAGES[LANG]["log_no_more_co"])
                                    log(market, "%s %s. %s %s" % (LANGUAGES[LANG]["log_current_price"], current_price, LANGUAGES[LANG]["log_liquidation_price"], liquidation))
                                    log(market, "%s %s" % (LANGUAGES[LANG]["log_avr_buy_price_is"], pos_average))#, LANGUAGES[LANG]["average_price_delta"], roe_pcnt, pnl, q_pair))
                                    if EXIT_STOP_LOSS_LEVEL != 0 and EXIT_STOP_LOSS_LEVEL != 111:
                                        if side == 'buy':
                                            stop_loss_price = round(pos_average - pos_average * EXIT_STOP_LOSS_LEVEL / 100, pricePrecision)
                                        else:
                                            stop_loss_price = round(pos_average + pos_average * EXIT_STOP_LOSS_LEVEL / 100, pricePrecision)
                                        log(market, "%s %s" % (LANGUAGES[LANG]["log_planning_stop_loss_price"], stop_loss_price))
                                    if EXIT_STOP_LOSS_LEVEL == 111:
                                        stop_order_q = """SELECT order_price FROM orders WHERE market='%s' AND stop_loss=1 AND order_filled IS NULL AND order_cancelled IS NULL  ORDER BY order_created DESC LIMIT 1""" % (market)
                                        cursor.execute(stop_order_q)
                                        stop_order = cursor.fetchone()
                                        if stop_order:
                                            stop_loss_price = stop_order[0]
                                            log(market, "%s %s" % (LANGUAGES[LANG]["log_stop_loss_price"], stop_loss_price))
                                        else:
                                            if side == 'buy':
                                                stop_loss_price = stop_loss_price_long
                                            else:
                                                stop_loss_price = stop_loss_price_short
                                            log(market, "%s %s" % (LANGUAGES[LANG]["log_planning_stop_loss_price"], stop_loss_price))
                                    log(market, "%s %s %s. %s: %s %s" % (LANGUAGES[LANG]["log_next_avr_for_manual"], next_avr_cost, q_pair, LANGUAGES[LANG]["log_free"], free, q_pair))


                            for order in orders_info:
                                #ПЕРЕКЛЮЧЕНИЕ ТАЙМФРЕЙМОВ
                                if TIMEFRAME_SWITCHING == True and ACTIVE_ORDERS == 0 and sell_count > 0 and not state["manual_averaging"].get():
                                    tf_switched = if_tf_switched(market)
                                    if tf_switched + 1 >= len(all_timeframes):
                                        tf = len(all_timeframes) - 1
                                    else:
                                        tf = tf_switched + 1
                                    TIMEFRAME = all_timeframes[tf]
                                    #price_0 = get_base_order_price(market, side, get_deal_number(market))
                                    price_last = get_price_last(market, side)

                                    # if sell_count and sell_count == 1:
                                    #     price_new = price_last - price_0 * (OVERLAP_PRICE * FIRST_CO_KOEFF / 100)
                                    # if sell_count and sell_count > 1:
                                    #     price_new = price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100

                                    if side == 'buy':
                                        if sell_count == 1:
                                            price_new = price_last - price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                        if sell_count > 1:
                                            price_new = price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100
                                    elif side == 'sell':
                                        if sell_count == 1:
                                            price_new = price_last + price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                        if sell_count > 1:
                                            price_new = price_last + price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100

                                    if (side == 'buy' and current_price < price_new) or (side == 'sell' and current_price > price_new):
                                        initial_tf = get_initial_tf(market)
                                        initial_stoch_long = get_initial_stoch_long(market)
                                        initial_stoch_short = get_initial_stoch_short(market)

                                        if initial_tf != 0:
                                            RECORD_TIMEFRAME = initial_tf
                                        else:
                                            RECORD_TIMEFRAME = TIMEFRAME

                                        if AVG_PRESET == 'STOCH_RSI':
                                            AVG_STOCH_LONG_UP_LEVEL = AVG_STOCH_S_LONG_UP_LEVEL
                                            AVG_STOCH_SHORT_LOW_LEVEL = AVG_STOCH_S_SHORT_LOW_LEVEL
                                        else:
                                            AVG_STOCH_LONG_UP_LEVEL = AVG_STOCH_C_LONG_UP_LEVEL
                                            AVG_STOCH_SHORT_LOW_LEVEL = AVG_STOCH_C_SHORT_LOW_LEVEL

                                        if initial_stoch_long != 0:
                                            RECORD_STOCH_LONG_LEVEL = initial_stoch_long
                                        else:
                                            RECORD_STOCH_LONG_LEVEL = AVG_STOCH_LONG_UP_LEVEL

                                        if initial_stoch_short != 0:
                                            RECORD_STOCH_SHORT_LEVEL = initial_stoch_short
                                        else:
                                            RECORD_STOCH_SHORT_LEVEL = AVG_STOCH_SHORT_LOW_LEVEL

                                        i_ema_reason = get_ema_reason(market)
                                        i_order_count_reason = get_order_count_reason(market)
                                        i_candle_count_reason = get_candle_count_reason(market)
                                        i_stoch_reason = get_stoch_reason(market)
                                        record_timeframe(market=market, timeframe_switch=tf_switched,
                                                         initial_tf=RECORD_TIMEFRAME, initial_stoch_long=RECORD_STOCH_LONG_LEVEL, initial_stoch_short=RECORD_STOCH_SHORT_LEVEL,
                                                         ema_reason=i_ema_reason, order_count_reason=i_order_count_reason, candle_count_reason=i_candle_count_reason, stoch_reason=i_stoch_reason)
                                        date_begin_q = """
                                               SELECT
                                                   order_filled
                                               FROM
                                                   orders
                                               WHERE
                                                   market='%s'
                                                   AND order_side = '%s'
                                                   AND order_filled IS NOT NULL
                                                   AND order_cancelled IS NULL
                                               ORDER BY order_created DESC
                                               LIMIT '%s'
                                             """ % (market, side, sell_count + 1)
                                        cursor.execute(date_begin_q)
                                        date_b = cursor.fetchone()

                                        initial_tf = get_initial_tf(market)



                                        if initial_tf != 0:
                                            UPDATE_TIMEFRAME = initial_tf
                                        else:
                                            UPDATE_TIMEFRAME = TIMEFRAME


                                        if AVG_PRESET == 'STOCH_RSI':
                                            AVG_STOCH_LONG_UP_LEVEL = AVG_STOCH_S_LONG_UP_LEVEL
                                            AVG_STOCH_SHORT_LOW_LEVEL = AVG_STOCH_S_SHORT_LOW_LEVEL
                                        else:
                                            AVG_STOCH_LONG_UP_LEVEL = AVG_STOCH_C_LONG_UP_LEVEL
                                            AVG_STOCH_SHORT_LOW_LEVEL = AVG_STOCH_C_SHORT_LOW_LEVEL

                                        if initial_stoch_long != 0:
                                            UPDATE_STOCH_LONG_LEVEL = initial_stoch_long
                                        else:
                                            UPDATE_STOCH_LONG_LEVEL = AVG_STOCH_LONG_UP_LEVEL

                                        if initial_stoch_short != 0:
                                            UPDATE_STOCH_SHORT_LEVEL = initial_stoch_short
                                        else:
                                            UPDATE_STOCH_SHORT_LEVEL = AVG_STOCH_SHORT_LOW_LEVEL


                                        if date_b != None:
                                            date_begin = date_b[0]
                                            t = time.strptime(date_begin, '%Y-%m-%d %H:%M:%S')
                                            order_time = utc_to_local_timezone(int(time.mktime(t)))
                                            time_passed = int(time.time()) - order_time
                                            # print(time_passed)

                                            k = {'1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '2h': 120, '4h': 240, '8h': 480, '12h': 720, '1d': 1440}

                                            candles_nomber = int(time_passed / (k[UPDATE_TIMEFRAME] * 60))
                                            # print(candles_nomber)
                                        else:
                                            candles_nomber = 1

                                        if tf_switched + 1 >= len(all_timeframes):
                                            tf = len(all_timeframes)-1
                                        else:
                                            tf = tf_switched + 1

                                        NEW_TIMEFRAME = all_timeframes[tf]

                                        if NEW_TIMEFRAME != GLOBAL_TF:
                                            new_timeframe_indicators_advice = await get_indicators_advice(config, market, NEW_TIMEFRAME, 'avg')
                                            new_fast = new_timeframe_indicators_advice['fast']
                                            new_slow = new_timeframe_indicators_advice['slow']

                                        else:
                                            new_fast = fast
                                            new_slow = slow


                                        if side == 'buy':
                                            ema_global_down = ema_global - (ema_global * EMA200_DELTA) / 100
                                            long_adj = int(UPDATE_STOCH_LONG_LEVEL + (UPDATE_STOCH_LONG_LEVEL * STOCH_ADJUSTMENT) / 100)
                                            short_adj = initial_stoch_short
                                        else:
                                            ema_global_down = ema_global + (ema_global * EMA200_DELTA) / 100
                                            short_adj = int(UPDATE_STOCH_SHORT_LEVEL - (UPDATE_STOCH_SHORT_LEVEL * STOCH_ADJUSTMENT) / 100)
                                            long_adj = initial_stoch_long

                                        if side == 'buy':
                                            if (EMA_GLOBAL_SWITCH == True and current_price < ema_global_down and price_last > ema_global) or \
                                                    (ORDERS_SWITCH == True and sell_count > ORDERS_COUNT - 1) or \
                                                    (LAST_CANDLE_SWITCH == True and candles_nomber > LAST_CANDLE_COUNT and sell_count > LAST_CANDLE_ORDERS - 1) or \
                                                    (new_slow < long_adj and new_fast < long_adj):

                                                if EMA_GLOBAL_SWITCH == True and current_price < ema_global_down and price_last > ema_global and i_ema_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=1, order_count_reason=0, candle_count_reason=0, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_ema_long"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))
                                                if ORDERS_SWITCH == True and sell_count > ORDERS_COUNT - 1 and i_order_count_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=1, candle_count_reason=0, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_order"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))
                                                if LAST_CANDLE_SWITCH == True and candles_nomber > LAST_CANDLE_COUNT and sell_count > LAST_CANDLE_ORDERS - 1 and i_candle_count_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=0, candle_count_reason=1, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_candle_long"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))

                                                if new_slow < long_adj and new_fast < long_adj and i_stoch_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=0, candle_count_reason=0, stoch_reason=1)
                                                    log(market, '%s %s. %s %s' % (text_stoch, LANGUAGES[LANG]["log_tf_switch_reason_stoch"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))
                                        else:
                                            if (EMA_GLOBAL_SWITCH == True and current_price > ema_global_down and price_last < ema_global) or \
                                                    (ORDERS_SWITCH == True and sell_count > ORDERS_COUNT - 1) or \
                                                    (LAST_CANDLE_SWITCH == True and candles_nomber > LAST_CANDLE_COUNT and sell_count > LAST_CANDLE_ORDERS - 1) or \
                                                    (new_slow > short_adj and new_fast > short_adj):

                                                if EMA_GLOBAL_SWITCH == True and current_price > ema_global_down and price_last < ema_global and i_ema_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=1, order_count_reason=0, candle_count_reason=0, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_ema_long"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))
                                                if ORDERS_SWITCH == True and sell_count > ORDERS_COUNT - 1 and i_order_count_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=1, candle_count_reason=0, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_order"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))
                                                if LAST_CANDLE_SWITCH == True and candles_nomber > LAST_CANDLE_COUNT and sell_count > LAST_CANDLE_ORDERS - 1 and i_candle_count_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=0, candle_count_reason=1, stoch_reason=0)
                                                    log(market, '%s. %s %s' % (LANGUAGES[LANG]["log_tf_switch_reason_candle_long"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))

                                                if new_slow > short_adj and new_fast > short_adj and i_stoch_reason != 1:
                                                    record_timeframe(market=market, timeframe_switch=tf, initial_tf=NEW_TIMEFRAME, initial_stoch_long=long_adj, initial_stoch_short=short_adj, ema_reason=0, order_count_reason=0, candle_count_reason=0, stoch_reason=1)
                                                    log(market, '%s %s. %s %s' % (text_stoch, LANGUAGES[LANG]["log_tf_switch_reason_stoch"], LANGUAGES[LANG]["log_timeframe_switched"], NEW_TIMEFRAME))



                                #print('not_filled_buy', not_filled_buy)
                                if state["manual_averaging"].get():
                                    avg_market = state["selected_coin"].get()

                                    if market == avg_market or len(config.get_value("bot", "base_coin").replace(' ', '').split(',')) < 2:
                                        log(market, '%s' % LANGUAGES[LANG]["log_manual_averaging_ok"])

                                        if not_filled_buy != None and sell_count == 0:
                                            cursor.execute(
                                                """
                                                  UPDATE counters
                                                  SET
                                                    counter_count=:new_count,
                                                    orders_total=:orders_total
                                                  WHERE
                                                    counter_market = :market
                                                """, {
                                                    'new_count': ORDERS_TOTAL,
                                                    'orders_total': ORDERS_TOTAL + 1,
                                                    'market': market
                                                }
                                            )
                                            conn.commit()

                                        try:
                                            await create_limit(market, side, global_strategy, 1, current_price, pos_amount, 'avg')

                                        except Exception as e:
                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 03', type(e).__name__, str(e)))
                                            if USE_TELEGRAM:
                                                try:
                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 03 ' + type(e).__name__ + str(e)))
                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                            state["needed_stop"] = True
                                            state["fixed_profit"] = True
                                            await asyncio.sleep(0.1)
                                            return
                                        record_trend(market=market, table="trend_avg", trend=global_ind['trend'], flag="1", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=0)


                                        state["manual_averaging"].set(False)
                                        break

                                if not orders_info[order]['order_filled'] and not orders_info[order]['order_cancelled']:
                                    try:
                                        stop_loss_id = get_open_stop_order(market, anti_side, get_deal_number(market))
                                        if stop_loss_id and stop_loss_id == orders_info[order]['order_id']:
                                            ord_type = 'stop_loss'
                                        else:
                                            ord_type = 'market'


                                        order_info = await connector.get_order(orders_info[order]['order_id'], market, ord_type)


                                    except Exception as e:
                                        log(market, '%s: %s %s' % ('GET ORDERS ERROR 02', type(e).__name__, str(e)))

                                    #log(market, 'Проверяем ордеры')
                                    if order_info['status'] == 'closed':
                                        balance = float(q['balance'])
                                        # deal_number = get_deal_number(market)
                                        # last_balance_q = """SELECT balance FROM orders WHERE market='%s' AND order_side='%s' AND deal_number='%s'ORDER BY order_created DESC""" % (market, side, deal_number)
                                        # cursor.execute(last_balance_q)
                                        # last_balance = cursor.fetchone()[0]
                                        #
                                        # base_order_balance = get_base_order_balance(market, side, deal_number)
                                        #
                                        # if orders_info[order]['order_side'] == anti_side:
                                        #     pnl = balance - last_balance
                                        #     deal_profit = balance - base_order_balance
                                        # else:
                                        #     pnl = 0
                                        #     deal_profit = 0
                                        #     #log_deal_length = deal_length(market, side)

                                        cancelled_ord_amount_q = """SELECT order_amount FROM orders WHERE market='%s' AND order_side = '%s' AND order_filled IS NULL AND order_cancelled IS NOT NULL ORDER BY order_created DESC LIMIT 2""" % (market, anti_side)
                                        cursor.execute(cancelled_ord_amount_q)
                                        cancelled_ord_amount = cursor.fetchone()

                                        if_stop_loss_q = """SELECT stop_loss FROM orders WHERE market='%s' AND order_side = '%s' AND order_filled IS NULL AND order_cancelled IS NULL ORDER BY order_created DESC LIMIT 1""" % (market, anti_side)
                                        cursor.execute(if_stop_loss_q)
                                        if_stop_loss = cursor.fetchone()

                                        if orders_info[order]['order_side'] == anti_side and cancelled_ord_amount != None and order_info['amount'] < cancelled_ord_amount[0] and if_stop_loss != None and if_stop_loss == 0:
                                            pass
                                        else:
                                            # if sell_remaining == True:
                                            #     cursor.execute("""UPDATE orders SET order_filled=datetime(), order_price=:order_price WHERE order_id = :order_id""", {'order_id': order, 'order_price': order_info['price']})
                                            #     conn.commit()
                                            # else:
                                            #cursor.execute("""UPDATE orders SET order_filled=datetime(), order_price=:order_price, balance=:balance, profit=:profit WHERE order_id=:order_id""", {'order_id': order, 'order_price': order_info['price'], 'balance': balance, 'profit': deal_profit})
                                            cursor.execute("""UPDATE orders SET order_filled=datetime(), order_price=:order_price, profit=:profit WHERE order_id=:order_id""", {'order_id': order, 'order_price': order_info['price'], 'profit': 0})
                                            conn.commit()

                                            orders_info[order]['order_filled'] = datetime.now()

                                    elif order_info['status'] == 'canceled':
                                        #if EXIT_METHOD == 'profit_exit':
                                        #log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], order, LANGUAGES[LANG]["log_order_canceled"]))
                                        cursor.execute("""UPDATE orders SET order_cancelled=datetime(), balance=:balance, profit=:profit WHERE order_id=:order_id""", {'order_id': order, 'balance': 0, 'profit': 0})
                                        conn.commit()

                                    else:
                                        #log(market, "%s-%s %s %s %s %s %s" % (orders_info[order]['order_side'], LANGUAGES[LANG]["log_order_with_amount"], orders_info[order]['order_amount'], b_pair, LANGUAGES[LANG]["log_order_with_price"], orders_info[order]['order_price'], LANGUAGES[LANG]["log_order_not_filled_yet"]))
                                        if order_info['remaining'] != order_info['amount']:
                                            orders_info[order]['partially_filled'] = True

                                    if orders_info[order]['order_side'] == side:
                                        #print('orders_info=', orders_info[order]['order_id'])
                                        if orders_info[order]['order_filled']:
                                            #o_amount = orders_info[order]['order_amount']
                                            #o_price = float(orders_info[order]['order_price'])
                                            log(market, '%s %s %s %s %s %s %s' % (LANGUAGES[LANG]["telegram_filled"], side, LANGUAGES[LANG]["log_with_amount"], order_info['amount'], b_pair, LANGUAGES[LANG]["telegram_for"], order_info['price']))
                                            sell_order_q = """SELECT order_id FROM orders WHERE market='%s' AND order_side = '%s' AND stop_loss=0 AND order_filled IS NULL AND order_cancelled IS NULL ORDER BY order_created DESC LIMIT 1""" % (market, anti_side)
                                            cursor.execute(sell_order_q)
                                            anti_order = cursor.fetchone()

                                            stop_order_q = """SELECT order_id FROM orders WHERE market='%s' AND stop_loss=1 AND order_filled IS NULL AND order_cancelled IS NULL  ORDER BY order_created DESC LIMIT 1""" % (market)
                                            cursor.execute(stop_order_q)
                                            stop_order = cursor.fetchone()

                                            if USE_TELEGRAM and only_for_fixes == False:
                                                log(market, '%s' % LANGUAGES[LANG]["log_telegram"])
                                                try:
                                                    send_msg("{}\n{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo,
                                                                                 '✅ ' + LANGUAGES[LANG]["telegram_filled"] + ' ' + side + ' ' + LANGUAGES[LANG]["telegram_for"] + ' ' + str(order_info['price']),
                                                                                 '💰 ' + LANGUAGES[LANG]["log_free_balance"] + ' ' + str(round(balance, 2)) + ' ' + q_pair
                                                    ))#'😱' '⚠' '📣' '🤑'
                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                            #if STEP_ONE > 0.01:


                                            if anti_order:
                                                is_partially_filled = False

                                                if 'partially_filled' in order:
                                                    is_partially_filled = order['partially_filled']
                                                else:
                                                    try:
                                                        #print('STOP QWER 1')
                                                        stop_loss_id = get_open_stop_order(market, anti_side, get_deal_number(market))
                                                        if stop_loss_id and stop_loss_id == anti_order[0]:
                                                            ord_type = 'stop_loss'
                                                        else:
                                                            ord_type = 'market'
                                                        #print('STOP QWER 2')
                                                        current_order_info = await connector.get_order(anti_order[0], market, ord_type)
                                                    except Exception as e:
                                                        log(market, '%s: %s %s' % ('GET ORDER ERROR 03', type(e).__name__, str(e)))
                                                    if current_order_info['remaining'] != current_order_info['amount'] and current_order_info['status'] == 'open':
                                                        is_partially_filled = True

                                                if not is_partially_filled:
                                                    if open_orders_count(market, anti_side) > 0:
                                                        try:
                                                            response = await connector.cancel_order(anti_order[0], market)
                                                            if response:
                                                                cancel_order_id(anti_order[0])
                                                                log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], anti_order[0], LANGUAGES[LANG]["log_order_market_canceled_DB"]))

                                                            if stop_order:
                                                                response = await connector.cancel_order(stop_order[0], market)
                                                                if response:
                                                                    cancel_order_id(stop_order[0])
                                                                    log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], stop_order[0], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                        except Exception as e:
                                                            c = True#log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 01', type(e).__name__, str(e)))


                                            #print(pos_amount)
                                            record_trend(market=market, table="trend_avg", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=ind['extreme_min'] if side == 'buy' else ind['extreme_max'])
                                            try:
                                                try:
                                                    q = await connector.get_balance(b_pair, q_pair, config)  # Берем данные по позе: balance, pnl, pos_average, leverage, pos_amount, pos_cost, pos_id, roe_pcnt
                                                except Exception as e:
                                                    pass
                                                    await asyncio.sleep(1)
                                                    try:
                                                        q = await connector.get_balance(b_pair, q_pair, config)
                                                    except Exception as e:
                                                        log(market, '%s: %s' % ('GET BALANCE ERROR 02', str(e)))

                                                balance = float(q['balance'])

                                                if len(q) > 1:
                                                    pnl = q['pnl']
                                                    pos_average = q['pos_average']
                                                    pos_amount = abs(q['pos_amount'])
                                                    pos_cost = q['pos_cost']
                                                    roe_pcnt = q['roe_pcnt']
                                                    leverage = q['leverage']
                                                    liquidation = q['liquidation']
                                                    free = q['free']
                                                    if q['side'] == 'long':
                                                        side = 'buy'
                                                    else:
                                                        side = 'sell'
                                                else:
                                                    pnl = 0
                                                    pos_average = 0
                                                    pos_amount = 0
                                                    pos_cost = 0
                                                    roe_pcnt = 0
                                                    leverage = 0
                                                    liquidation = 0
                                                    free = balance

                                                if BACK_PROFIT != 0:
                                                    bp = get_bp(BACK_PROFIT, sell_count)
                                                else:
                                                    bp = 1

                                                if EXIT_METHOD == 'profit_exit':
                                                    if side == 'buy':
                                                        price_level = round(pos_average + pos_average * EXIT_PROFIT_LEVEL / bp / 100, pricePrecision)
                                                    else:
                                                        price_level = round(pos_average - pos_average * EXIT_PROFIT_LEVEL / bp / 100, pricePrecision)
                                                else:
                                                    if side == 'buy':
                                                        price_level = round(pos_average + pos_average * SQUEEZE_PROFIT / bp / 100, pricePrecision)
                                                    else:
                                                        price_level = round(pos_average - pos_average * SQUEEZE_PROFIT / bp / 100, pricePrecision)


                                                await create_take_profit(market=market, side=anti_side, global_strategy=global_strategy, immediate=0, amount=abs(pos_amount), price_level=price_level)

                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('TAKE PROFIT PLACEMENT ERROR 01', type(e).__name__, str(e)))
                                                if USE_TELEGRAM:
                                                    try:
                                                        send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'TAKE PROFIT PLACEMENT ERROR 01' + type(e).__name__ + str(e)))
                                                    except Exception as e:
                                                        log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                state["needed_stop"] = True
                                                state["fixed_profit"] = True
                                                await asyncio.sleep(0.1)
                                                return
                                            # Запускаем выставление доп. ордеров (Если активных ордеров > 0)
                                            if ACTIVE_ORDERS > 0 and open_orders_count(market, side) < ACTIVE_ORDERS and ACTIVE_ORDERS < ORDERS_TOTAL:
                                                #price_0 = get_base_order_price(market, side, get_deal_number(market))
                                                try:
                                                    await create_limit(market, side, global_strategy, 0, current_price, 0, 'avg')

                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('ERROR CREATE ADDITIONAL ACTIVE ORDER', type(e).__name__, str(e)))
                                                    if USE_TELEGRAM:
                                                        try:
                                                            send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'ERROR CREATE ADDITIONAL ACTIVE ORDER' + type(e).__name__ + str(e)))
                                                        except Exception as e:
                                                            log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                    state["needed_stop"] = True
                                                    state["fixed_profit"] = True
                                                    await asyncio.sleep(0.1)
                                                    return

                                    if orders_info[order]['order_side'] == anti_side:
                                        if state["manual_sell"].get():
                                            avg_market = state["selected_coin"].get()
                                            if market == avg_market or len(config.get_value("bot", "base_coin").replace(' ', '').split(',')) < 2:
                                                log(market, '%s' % LANGUAGES[LANG]["log_manual_sell_ok"])
                                                for unrealized_order in orders_info:
                                                    if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                        try:
                                                            response = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                            if response:
                                                                cancel_order_id(orders_info[unrealized_order]['order_id'])
                                                                log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], unrealized_order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                        except Exception as e:
                                                            c = True#log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 02', type(e).__name__, str(e)))

                                                record_trend(market=market, table="trend_avg", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=ind['extreme_min'] if side == 'buy' else ind['extreme_max'])
                                                await create_market(market=market, side=anti_side, global_strategy=global_strategy, remaining_amount=order_info['remaining'], reason='sell_button')
                                                state["manual_sell"].set(False)
                                                break

                                        if ACTIVE_ORDERS == 0:

                                            sell_count = get_sell_counter(market)

                                            if pnl < 0 and not orders_info[order]['order_filled'] and order_info['status'] != 'canceled' and sell_count > 0:
                                                sell_order_price_q = """SELECT order_price FROM orders WHERE market='%s' AND order_side = '%s' AND order_filled IS NULL AND order_cancelled IS NULL ORDER BY order_created DESC LIMIT 1""" % (market, anti_side)
                                                cursor.execute(sell_order_price_q)
                                                anti_order_price = cursor.fetchone()[0]

                                                # Проверка не достигнута ли цена для следующего бая. Если да, то запускаем бай-функцию.
                                                log(market, '%s' % LANGUAGES[LANG]["log_dynamic_on"])
                                                log(market, '%s' % LANGUAGES[LANG]["log_check_avarage_"+side])

                                                sell_count = get_sell_counter(market)

                                                price_0 = get_base_order_price(market, side, get_deal_number(market))
                                                date_0 = get_base_order_date(market, side, get_deal_number(market))

                                                t = time.strptime(date_0, '%Y-%m-%d %H:%M:%S')

                                                if side == 'buy':
                                                    if EXIT_METHOD != 'profit_exit':
                                                        p_side = LANGUAGES[LANG]["telegram_squeeze_sold"]
                                                    else:
                                                        p_side = LANGUAGES[LANG]["telegram_sold"]
                                                else:
                                                    if EXIT_METHOD != 'profit_exit':
                                                        p_side = LANGUAGES[LANG]["telegram_squeeze_bought"]
                                                    else:
                                                        p_side = LANGUAGES[LANG]["telegram_bought"]
                                                log(market, "%s %s (%s %s %s)" % (LANGUAGES[LANG]["log_close_price"], anti_order_price, p_side, abs(pos_amount), b_pair))
                                                log(market, "%s %s. %s %s" % (LANGUAGES[LANG]["log_avr_buy_price_is"], pos_average, LANGUAGES[LANG]["log_current_price"], current_price))#LANGUAGES[LANG]["average_price_delta"], roe_pcnt, pnl, q_pair

                                                if EXIT_STOP_LOSS_LEVEL != 0 and EXIT_STOP_LOSS_LEVEL != 111:
                                                    if side == 'buy':
                                                        stop_loss_price = pos_average - pos_average * abs(EXIT_STOP_LOSS_LEVEL) / 100
                                                    else:
                                                        stop_loss_price = pos_average + pos_average * abs(EXIT_STOP_LOSS_LEVEL) / 100
                                                    log(market, "%s %s" % (LANGUAGES[LANG]["log_planning_stop_loss_price"], stop_loss_price))

                                                if EXIT_STOP_LOSS_LEVEL == 111:
                                                    stop_order_q = """SELECT order_price FROM orders WHERE market='%s' AND stop_loss=1 AND order_filled IS NULL AND order_cancelled IS NULL  ORDER BY order_created DESC LIMIT 1""" % (market)
                                                    cursor.execute(stop_order_q)
                                                    stop_order = cursor.fetchone()
                                                    if stop_order:
                                                        stop_loss_price = stop_order[0]
                                                        log(market, "%s %s" % (LANGUAGES[LANG]["log_stop_loss_price"], stop_loss_price))
                                                    else:
                                                        if side == 'buy':
                                                            stop_loss_price = stop_loss_price_long
                                                        else:
                                                            stop_loss_price = stop_loss_price_short
                                                        log(market, "%s %s" % (LANGUAGES[LANG]["log_planning_stop_loss_price"], stop_loss_price))

                                                if USE_TELEGRAM:
                                                    if_bo_order_check_q = """SELECT checked_date FROM bo_order_check WHERE market='%s' ORDER BY rowid DESC LIMIT 1""" % market
                                                    cursor.execute(if_bo_order_check_q)
                                                    if_bo_order_check = cursor.fetchone()
                                                    if if_bo_order_check == None or if_bo_order_check == 0:
                                                        new_date_0 = 0
                                                    else:
                                                        new_date_0 = if_bo_order_check[0]

                                                    t = int(datetime.strptime(date_0, '%Y-%m-%d %H:%M:%S').timestamp())
                                                    time_passed = (int(time.time()) - t) / 60 / 60 / 24

                                                    if new_date_0 == 0:
                                                        if time_passed > 5:
                                                            try:
                                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo, '✅ ' + LANGUAGES[LANG]["log_5_days_from_BO"]))
                                                            except Exception as e:
                                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                            cursor.execute("""INSERT OR REPLACE INTO bo_order_check(market, checked_date) values(:market, datetime())""", {'market': market})
                                                            conn.commit()
                                                    else:
                                                        cursor.execute("""SELECT checked_date FROM bo_order_check WHERE market='%s' ORDER BY rowid DESC LIMIT 1""" % market)
                                                        new_date_0 = cursor.fetchone()[0]
                                                        #print(new_date_0)
                                                        new_t = int(datetime.strptime(new_date_0, '%Y-%m-%d %H:%M:%S').timestamp())
                                                        new_time_passed = (int(time.time()) - new_t) / 60 / 60 / 24

                                                        if new_time_passed > 5:
                                                            try:
                                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo, '✅ ' + LANGUAGES[LANG]["log_5_days_from_BO"]))
                                                            except Exception as e:
                                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                            cursor.execute("""UPDATE bo_order_check SET checked_date=datetime() WHERE market='%s'""" % market)
                                                            conn.commit()

                                                price_last = get_price_last(market, side)

                                                if side == 'buy':
                                                    if sell_count == 1:
                                                        price_new = price_last - price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                                    if sell_count > 1:
                                                        price_new = price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100
                                                elif side == 'sell':
                                                    if sell_count == 1:
                                                        price_new = price_last + price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                                    if sell_count > 1:
                                                        price_new = price_last + price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100
                                                else:
                                                    price_new = 0
                                                #print('price_new', price_new)
                                                #print('current_price', current_price)
                                                #print('side', side, 'price_last', price_last, 'price_new', price_new)
                                                #await asyncio.sleep(130)
                                                log(market, '%s %s' % (LANGUAGES[LANG]["log_next_avarage_"+side+"_price"], round(price_new, pricePrecision)))

                                                if (side == 'buy' and current_price > price_new) or (side == 'sell' and current_price < price_new):
                                                    log(market, '%s' % LANGUAGES[LANG]["log_no_avarage"])
                                                if (side == 'buy' and current_price < price_new) or (side == 'sell' and current_price > price_new):
                                                    margin_flag = 0
                                                    if side == 'buy': log(market, '%s' % LANGUAGES[LANG]["log_start_avarage_long"])
                                                    if side == 'sell': log(market, '%s' % LANGUAGES[LANG]["log_start_avarage_short"])
                                                    if USE_MARGIN == False or (USE_MARGIN == True and MARGIN_BOTTOM < current_price < MARGIN_TOP):
                                                        if USE_MARGIN == True: log(market, '%s' % LANGUAGES[LANG]["log_good_margin"])

                                                        # ДИНАМИЧЕСКОЕ УСРЕДНЕНИЕ ПО STOCH + MACD + BB + EMA

                                                        flag = get_flag(market=market, table="trend_avg")
                                                        flag_to_exit = 0
                                                        while flag == "0" and flag_to_exit == 0:
                                                            #print(MARKETS)
                                                            #for market in MARKETS:
                                                            if flag_to_exit == 1:
                                                                break

                                                            AVG_PRESET = config.get_value("averaging", "avg_preset")

                                                            AVG_TF = get_initial_tf(market)

                                                            AVG_TIMESLEEP = config.get_value("averaging", "avg_timesleep")

                                                            # if balance < 5:
                                                            #     log(market, '%s' % (LANGUAGES[LANG]["no_balance"]))
                                                            #
                                                            #     if len(base_coins) < 2:
                                                            #         state["needed_stop"] = True
                                                            #         state["fixed_profit"] = True
                                                            #         await asyncio.sleep(0.1)
                                                            #         break
                                                            #     else:
                                                            #         continue
                                                            #else:
                                                            try:
                                                                global_ind = await get_indicators_advice(config, market, GLOBAL_TF, 'avg')
                                                                ind = await get_indicators_advice(config, market, AVG_TF, 'avg')
                                                                fast_global = global_ind['fast']
                                                                slow_global = global_ind['slow']
                                                                global_strategy = global_ind['trend']
                                                            except Exception as e:
                                                                log(market, '%s: %s %s' % ('ERROR', type(e).__name__, str(e)))

                                                            macd_log = "MACD"
                                                            bb_log = "BB:"
                                                            ema_200_log = "EMA200"


                                                            current_price = ind['close_1']


                                                            if side == 'buy':
                                                                limit_price = round(current_price * (1 + 10 * LIMIT_STOP / 100), pricePrecision)
                                                            else:
                                                                limit_price = round(current_price / (1 + 10 * LIMIT_STOP / 100), pricePrecision)

                                                            price_0 = get_base_order_price(market, side, get_deal_number(market))
                                                            price_last = get_price_last(market, side)
                                                            date_last = get_date_last(market, side)

                                                            t = time.strptime(date_last, '%Y-%m-%d %H:%M:%S')
                                                            order_time = utc_to_local_timezone(int(time.mktime(t)))
                                                            time_passed = int(time.time()) - order_time
                                                            time_left_sec = NEW_ORDER_TIME - time_passed


                                                            if state["manual_averaging"].get():
                                                                avg_market = state["selected_coin"].get()
                                                                if market == avg_market or len(config.get_value("bot", "base_coin").replace(' ', '').split(',')) < 2:
                                                                    break
                                                                break

                                                            if sell_count and sell_count == 1:
                                                                if side == 'buy':
                                                                    price_new = round(price_last - price_0 * (OVERLAP_PRICE * FIRST_CO_KOEFF / 100), pricePrecision)
                                                                else:
                                                                    price_new = round(price_last + price_0 * (OVERLAP_PRICE * FIRST_CO_KOEFF / 100), pricePrecision)

                                                            if sell_count and sell_count > 1:
                                                                if side == 'buy':
                                                                    price_new = round(price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100, pricePrecision)
                                                                else:
                                                                    price_new = round(price_last + price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100, pricePrecision)

                                                            if side == 'buy' and current_price >= price_new:
                                                                log(market, '%s' % (LANGUAGES[LANG]["price_go_up_long"]))
                                                            if side == 'sell' and current_price <= price_new:
                                                                log(market, '%s' % (LANGUAGES[LANG]["price_go_down_short"]))

                                                            if time_passed < NEW_ORDER_TIME and sell_count > 1:
                                                                log(market, 'please wait', time_left_sec, 'sec.')
                                                                # break
                                                            #print(current_price, price_new)
                                                            if sell_count > 0 and EMERGENCY_AVERAGING != 0 and price_new and abs(current_price/price_new-1) * 100 > EMERGENCY_AVERAGING:
                                                                log(market, '%s' % LANGUAGES[LANG]["log_emergency_averaging"])
                                                                flag = get_flag(market=market, table="trend_avg")
                                                                if flag == "0":
                                                                    try:
                                                                        await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                    except Exception as e:
                                                                        log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 04', type(e).__name__, str(e)))
                                                                        if USE_TELEGRAM:
                                                                            try:
                                                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 04 ' + type(e).__name__ + str(e)))
                                                                            except Exception as e:
                                                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                        state["needed_stop"] = True
                                                                        state["fixed_profit"] = True
                                                                        await asyncio.sleep(0.1)
                                                                        break
                                                                    finally:
                                                                        flag = "1"
                                                                        price_new = current_price
                                                                        break


                                                            if AVG_PRESET == "STOCH_CCI":
                                                                log(market, '%s: %s(%s)' % (LANGUAGES[LANG]["log_avg_preset_chosen"], AVG_PRESET, AVG_TF))
                                                                if (side == 'buy' and ((AVG_USE_STOCH_C and ind['slow'] > AVG_STOCH_C_LONG_UP_LEVEL) or (AVG_USE_CCI and ind['cci_1'] > AVG_CCI_LONG_LEVEL))) or side == 'sell' and ((AVG_USE_STOCH_C and ind['slow'] < AVG_STOCH_C_SHORT_LOW_LEVEL) or (AVG_USE_CCI and ind['cci_1'] < AVG_CCI_SHORT_LEVEL)):
                                                                    if side == 'buy': log(market, '%s %s' % (AVG_PRESET, LANGUAGES[LANG]["log_stoch_not_in_channel_long"]))
                                                                    else: log(market, '%s %s' % (AVG_PRESET, LANGUAGES[LANG]["log_stoch_not_in_channel_short"]))
                                                                STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_cci_answer(market, 'avg', side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], cci_3=ind['cci_3'], cci_2=ind['cci_2'], cci=ind['cci_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                                                #print(STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS)
                                                                #if current_price < price_new and fast > slow and fast < AVG_STOCH_LONG_UP_LEVEL and middle > current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE:
                                                                if STOCH_ALLOWS and CCI_ALLOWS and GLOBAL_STOCH_ALLOWS and ((side == 'buy' and current_price < price_new and ind['middle'] > current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE) or (side == 'sell' and current_price > price_new and ind['middle'] < current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE)):
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        log(market, '%s. %s' % (LANGUAGES[LANG]["trend_changes_avr_found"], LANGUAGES[LANG]["trend_changes_avr_price_is"]))
                                                                        log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price, LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                        if AVG_USE_STOCH_C == True: log(market, '%s %s: %s %0.3f, %s %0.3f, %s %s' % (AVG_TF, text_stoch, LANGUAGES[LANG]["fast_STOCH"], ind['fast'], LANGUAGES[LANG]["slow_STOCH"], ind['slow'], macd_log, round(ind['macd_h_1'],8)))
                                                                        if AVG_USE_CCI == True: log(market, "%s. %s %s: (%0.3f, %0.3f, %0.3f)" % (LANGUAGES[LANG]["log_cci_allows"], 'CCI', AVG_TF, round(ind['cci_3'], pricePrecision), round(ind['cci_2'], pricePrecision), round(ind['cci_1'], pricePrecision)))
                                                                        if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                        log(market, '%s: %s, %s: %s, %s: %s, %s: %s' % ('BB_u', round(ind['upper'], pricePrecision), 'BB_m', round(ind['middle'], pricePrecision), 'BB_l', round(ind['lower'], pricePrecision), ema_200_log, round(ind['ema200'], pricePrecision)))
                                                                        log(market, '---------------------------------------------------------------------------')

                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 05', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 05 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break


                                                                else:
                                                                    if (side == 'buy' and current_price < price_new and ((AVG_USE_STOCH_C and ind['slow'] < AVG_STOCH_C_LONG_UP_LEVEL) or (AVG_USE_CCI and ind['cci_1'] < AVG_CCI_LONG_LEVEL))) or (side == 'sell' and current_price > price_new and ((AVG_USE_STOCH_C and ind['slow'] > AVG_STOCH_C_LONG_UP_LEVEL) or (AVG_USE_CCI and ind['cci_1'] > AVG_CCI_LONG_LEVEL))):#Ищем точку разворота для усреднения позиции
                                                                        log(market, '%s' % (LANGUAGES[LANG]["no_trend_change"]))
                                                                    else:#"Ждем изменения цены или показания индикаторов"
                                                                        log(market, '%s' % (LANGUAGES[LANG]["price_check"]))
                                                                    log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price,  LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                    if AVG_USE_STOCH_C == True: log(market, '%s %s: %s %0.3f, %s %0.3f, %s %s' % (text_stoch, AVG_TF, LANGUAGES[LANG]["fast_STOCH"], ind['fast'], LANGUAGES[LANG]["slow_STOCH"], ind['slow'], macd_log, round(ind['macd_h_1'], 8)))
                                                                    if AVG_USE_CCI == True: log(market, "%s %s: (%0.3f, %0.3f, %0.3f)" % ('CCI', AVG_TF, round(ind['cci_3'], pricePrecision), round(ind['cci_2'], pricePrecision), round(ind['cci_1'], pricePrecision)))
                                                                    if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                    log(market, '%s: %s, %s: %s, %s: %s, %s: %s' % ('BB_u', round(ind['upper'], pricePrecision), 'BB_m', round(ind['middle'], pricePrecision), 'BB_l', round(ind['lower'], pricePrecision), ema_200_log, round(ind['ema200'], pricePrecision)))
                                                                    log(market, '---------------------------------------------------------------------------')



                                                            if AVG_PRESET == "STOCH_RSI":
                                                                log(market, '%s: %s(%s)' % (LANGUAGES[LANG]["log_avg_preset_chosen"], AVG_PRESET, AVG_TF))
                                                                print()
                                                                if (side == 'buy' and ((AVG_USE_STOCH_S and ind['slow'] > AVG_STOCH_S_LONG_UP_LEVEL) or (AVG_USE_RSI and ind['rsi_1'] > AVG_RSI_LONG_LEVEL))) or side == 'sell' and ((AVG_USE_STOCH_S and ind['slow'] < AVG_STOCH_S_SHORT_LOW_LEVEL) or (AVG_USE_RSI and ind['rsi_1'] < AVG_RSI_SHORT_LEVEL)):
                                                                    if side == 'buy': log(market, '%s %s' % (AVG_PRESET, LANGUAGES[LANG]["log_stoch_not_in_channel_long"]))
                                                                    else: log(market, '%s %s' % (AVG_PRESET, LANGUAGES[LANG]["log_stoch_not_in_channel_short"]))
                                                                STOCH_ALLOWS, RSI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_rsi_answer(market, 'avg', side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], rsi_3=ind['rsi_3'], rsi_2=ind['rsi_2'], rsi=ind['rsi_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])
                                                                #print(STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS)
                                                                #if current_price < price_new and fast > slow and fast < AVG_STOCH_LONG_UP_LEVEL and middle > current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE:
                                                                if STOCH_ALLOWS and RSI_ALLOWS and GLOBAL_STOCH_ALLOWS and ((side == 'buy' and current_price < price_new and ind['middle'] > current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE) or (side == 'sell' and current_price > price_new and ind['middle'] < current_price and abs(current_price/price_new-1) * 100 > CO_SAFETY_PRICE)):
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        log(market, '%s. %s' % (LANGUAGES[LANG]["trend_changes_avr_found"], LANGUAGES[LANG]["trend_changes_avr_price_is"]))
                                                                        log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price, LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                        if AVG_USE_STOCH_S == True: log(market, '%s %s: %s %0.3f, %s %0.3f, %s %s' % (AVG_TF, text_stoch, LANGUAGES[LANG]["fast_STOCH"], ind['fast'], LANGUAGES[LANG]["slow_STOCH"], ind['slow'], macd_log, round(ind['macd_h_1'],8)))
                                                                        if AVG_USE_RSI == True: log(market, "%s. %s %s: (%0.3f, %0.3f, %0.3f)" % (LANGUAGES[LANG]["log_rsi_allows"], 'RSI', AVG_TF, round(ind['rsi_3'], pricePrecision), round(ind['rsi_2'], pricePrecision), round(ind['rsi_1'], pricePrecision)))
                                                                        if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                        log(market, '%s: %s, %s: %s, %s: %s, %s: %s' % ('BB_u', round(ind['upper'], pricePrecision), 'BB_m', round(ind['middle'], pricePrecision), 'BB_l', round(ind['lower'], pricePrecision), ema_200_log, round(ind['ema200'], pricePrecision)))
                                                                        log(market, '---------------------------------------------------------------------------')

                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 05', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 05 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break


                                                                else:
                                                                    if (side == 'buy' and current_price < price_new and ((AVG_USE_STOCH_S and ind['slow'] < AVG_STOCH_S_LONG_UP_LEVEL) or (AVG_USE_RSI and ind['rsi_1'] < AVG_RSI_LONG_LEVEL))) or (side == 'sell' and current_price > price_new and ((AVG_USE_STOCH_S and ind['slow'] > AVG_STOCH_S_LONG_UP_LEVEL) or (AVG_USE_RSI and ind['rsi_1'] > AVG_RSI_LONG_LEVEL))):#Ищем точку разворота для усреднения позиции
                                                                        log(market, '%s' % (LANGUAGES[LANG]["no_trend_change"]))
                                                                    else:#"Ждем изменения цены или показания индикаторов"
                                                                        log(market, '%s' % (LANGUAGES[LANG]["price_check"]))
                                                                    log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price,  LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                    if AVG_USE_STOCH_S == True: log(market, '%s %s: %s %0.3f, %s %0.3f, %s %s' % (text_stoch, AVG_TF, LANGUAGES[LANG]["fast_STOCH"], ind['fast'], LANGUAGES[LANG]["slow_STOCH"], ind['slow'], macd_log, round(ind['macd_h_1'], 8)))
                                                                    if AVG_USE_RSI == True: log(market, "%s %s: (%0.3f, %0.3f, %0.3f)" % ('RSI', AVG_TF, round(ind['rsi_3'], pricePrecision), round(ind['rsi_2'], pricePrecision), round(ind['rsi_1'], pricePrecision)))
                                                                    if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                    log(market, '%s: %s, %s: %s, %s: %s, %s: %s' % ('BB_u', round(ind['upper'], pricePrecision), 'BB_m', round(ind['middle'], pricePrecision), 'BB_l', round(ind['lower'], pricePrecision), ema_200_log, round(ind['ema200'], pricePrecision)))
                                                                    log(market, '---------------------------------------------------------------------------')



                                                            if AVG_PRESET == "CCI_CROSS":
                                                                if AVG_CCI_CROSS_USE_PRICE == True:
                                                                    add_text = " + price"
                                                                else:
                                                                    add_text = ""
                                                                log(market, '%s: %s%s (%s)' % (LANGUAGES[LANG]["log_avg_preset_chosen"], AVG_PRESET, add_text, AVG_TF))
                                                                CCI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_cci_cross_answer(market, 'avg', side, current_price=current_price, cci=ind['cci_1'], cci_2=ind['cci_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                                if (side == 'buy' and current_price < price_new and CCI_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS) or (side == 'sell' and current_price > price_new and CCI_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS):
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        if AVG_CCI_CROSS_USE_PRICE == True:
                                                                            log(market, "%s %s" % (AVG_PRESET + "+ price", LANGUAGES[LANG]["log_xxx_allows_avg"]))
                                                                        else:
                                                                            log(market, "%s %s" % (AVG_PRESET, LANGUAGES[LANG]["log_xxx_allows_avg"]))
                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 06', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 06 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break

                                                                else:
                                                                    log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price,  LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                    if current_price < price_new and ((AVG_CCI_CROSS_USE_PRICE == True and ind['cci_1'] < AVG_CCI_CROSS_LONG_LEVEL) or (AVG_CCI_CROSS_USE_PRICE == False and ((AVG_CCI_CROSS_METHOD == "crossover" and ind['cci_1'] > AVG_CCI_CROSS_LONG_LEVEL) or (AVG_CCI_CROSS_METHOD == "crossunder" and ind['cci_1'] < AVG_CCI_CROSS_LONG_LEVEL)))):#Ищем точку разворота для усреднения позиции
                                                                        log(market, '%s' % (LANGUAGES[LANG]["no_trend_change"]))
                                                                    else:#"Ждем изменения цены или показания индикаторов"
                                                                        log(market, '%s' % (LANGUAGES[LANG]["price_check"]))
                                                                    if AVG_CCI_CROSS_USE_PRICE == False:
                                                                        log(market, "%s %s: (%0.3f, %0.3f, %0.3f)" % ('CCI', AVG_TF, round(ind['cci_3'], pricePrecision), round(ind['cci_2'], pricePrecision), round(ind['cci_1'], pricePrecision)))
                                                                    if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                    log(market, '---------------------------------------------------------------------------')


                                                            if AVG_PRESET == "MA_CROSS":
                                                                log(market, '%s: %s(%s)' % (LANGUAGES[LANG]["log_avg_preset_chosen"], AVG_PRESET, AVG_TF))
                                                                MA_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_ma_cross_answer(market, 'avg', side, current_price=current_price, ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], ma_1_prev=ind['ma_1_2'], ma_2_prev=ind['ma_2_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                                if (side == 'buy' and current_price < price_new and MA_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS) or (side == 'sell' and current_price > price_new and MA_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS):
                                                                    log(market, "%s %s %s" % (AVG_PRESET, AVG_TF, LANGUAGES[LANG]["log_xxx_allows_avg"]))
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 07', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 07 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break

                                                                else:
                                                                    log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price,  LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                    if current_price < price_new and AVG_MA_CROSS_METHOD == "crossover" and ind['ma_1_2'] < ind['ma_2_2']:
                                                                        log(market, '%s' % (LANGUAGES[LANG]["no_trend_change"]))
                                                                    else:
                                                                        log(market, '%s' % (LANGUAGES[LANG]["price_check"]))
                                                                    if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                    log(market, '---------------------------------------------------------------------------')

                                                            if AVG_PRESET == "RSI_SMARSI":
                                                                log(market, '%s: %s(%s)' % (LANGUAGES[LANG]["log_avg_preset_chosen"], AVG_PRESET, AVG_TF))
                                                                RSI_SMARSI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_rsi_smarsi_cross_answer(market, 'avg', side, current_price=current_price, rsi=ind['rsi_1'], smarsi=ind['smarsi'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                                if (side == 'buy' and current_price < price_new and RSI_SMARSI_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS) or (side == 'sell' and current_price > price_new and RSI_SMARSI_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS):
                                                                    log(market, "%s %s %s" % (AVG_PRESET, AVG_TF, LANGUAGES[LANG]["log_xxx_allows_avg"]))
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 08', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 08 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break

                                                                else:
                                                                    log(market, '%s %s. %s %s %s. %s %0.2f' % (LANGUAGES[LANG]["avr_order_level_was"], price_new, LANGUAGES[LANG]["log_current_price"], 'ask', current_price,  LANGUAGES[LANG]["price_delta"], (current_price / price_new-1) * 100), '%')
                                                                    if current_price < price_new and global_ind['smarsi'] < AVG_SMARSI_CROSS_LONG_UP_LEVEL:
                                                                        log(market, '%s' % (LANGUAGES[LANG]["no_trend_change"]))
                                                                    else:
                                                                        log(market, '%s' % (LANGUAGES[LANG]["price_check"]))
                                                                    if USE_GLOBAL_STOCH == True: log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                                    log(market, '---------------------------------------------------------------------------')

                                                            if AVG_PRESET == 'PRICE':
                                                                if (side == 'buy' and current_price < price_last - price_last * AVG_PRICE_DELTA_LONG / 100) or (side == 'sell' and current_price > price_last + price_last * AVG_PRICE_DELTA_SHORT / 100):
                                                                    log(f"{market} PRICE-пересет позволяет усредниться. Предыдущая цена {price_last}, текущая цена {current_price}")
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 1, current_price, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 08', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 08 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break
                                                                else:
                                                                    log(f"{market} PRICE-пересет не позволяет усредниться. Ждем изменения цены")


                                                            # ЛОГИКА УСРЕДНЕНИЯ MIDAS
                                                            if AVG_PRESET == "MIDAS":
                                                                MIDAS_ALLOWS = False

                                                                price_last = get_price_last(market, side)
                                                                if side == 'buy':
                                                                    if sell_count == 1:
                                                                        next_price = price_last - price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                                                    if sell_count > 1:
                                                                        next_price = price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100
                                                                elif side == 'sell':
                                                                    if sell_count == 1:
                                                                        next_price = price_last + price_last * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)
                                                                    if sell_count > 1:
                                                                        next_price = price_last + price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100
                                                                else:
                                                                    next_price = 0

                                                                new_qfl = ind['qfl_result']
                                                                new_base = ind['qfl_base']

                                                                if next_price and (side == 'buy' and (new_base and new_base < next_price and current_price < new_base - new_base * AVG_H_L_PERCENT / 100)) or \
                                                                        (side == 'sell' and (new_base and new_base > next_price and current_price > new_base + new_base * AVG_H_L_PERCENT / 100)):
                                                                    MIDAS_ALLOWS = True
                                                                    if side == 'buy':
                                                                        price_level = new_base - new_base * AVG_H_L_PERCENT / 100
                                                                    else:
                                                                        price_level = new_base + new_base * AVG_H_L_PERCENT / 100

                                                                # усредняемся
                                                                if MIDAS_ALLOWS == True:
                                                                    flag = get_flag(market=market, table="trend_avg")
                                                                    if flag == "0":
                                                                        try:
                                                                            await create_limit(market, side, global_strategy, 0, price_level, 0, 'avg')
                                                                        except Exception as e:
                                                                            log(market, '%s: %s %s' % ('CREATE LIMIT ORDER ERROR 09', type(e).__name__, str(e)))
                                                                            if USE_TELEGRAM:
                                                                                try:
                                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE LIMIT ORDER ERROR 09 ' + type(e).__name__ + str(e)))
                                                                                except Exception as e:
                                                                                    log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                            state["needed_stop"] = True
                                                                            state["fixed_profit"] = True
                                                                            await asyncio.sleep(0.1)
                                                                            break
                                                                        finally:
                                                                            log(market, 'ВЫСТАВЛЯЕМ УСРЕДНЕНИЕ ДЛЯ ', side)
                                                                            try:
                                                                                send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo, '✅ ' + 'ВЫСТАВЛЯЕМ УСРЕДНЕНИЕ ДЛЯ ' + side))  # , '💰 ' + str(LANGUAGES[LANG]["log_free_balance"]) + ' ' + str(q[0]) + ' ' + str(q_pair)))
                                                                            except Exception as e:
                                                                                log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                                                break
                                                                            flag = "1"
                                                                            price_new = current_price
                                                                            break

                                                            if AVG_PRESET == "MIDAS":
                                                                r_qfl_result = 0
                                                                r_qfl_base = 0
                                                            else:
                                                                r_qfl_result = 0
                                                                r_qfl_base = ind['extreme_min'] if side == 'buy' else ind['extreme_max']

                                                            if flag == '1': fff = '1'
                                                            else: fff = '0'
                                                            record_trend(market=market, table="trend_avg", trend=global_ind['trend'], flag=fff, ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=r_qfl_result, qfl_base=r_qfl_base)

                                                            TIME_SLEEP = AVG_TIMESLEEP




                                                            ff = False
                                                            for market in MARKETS:
                                                                price_0 = get_base_order_price(market, side, get_deal_number(market))
                                                                price_last = get_price_last(market, side)

                                                                if sell_count and sell_count == 1:
                                                                    if side == 'buy':
                                                                        price_new = round(price_last - price_0 * (OVERLAP_PRICE * FIRST_CO_KOEFF / 100), pricePrecision)
                                                                    else:
                                                                        price_new = round(price_last + price_0 * (OVERLAP_PRICE * FIRST_CO_KOEFF / 100), pricePrecision)

                                                                if sell_count and sell_count > 1:
                                                                    if side == 'buy':
                                                                        price_new = round(price_last - price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100, pricePrecision)
                                                                    else:
                                                                        price_new = round(price_last + price_last * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** sell_count) / 100, pricePrecision)

                                                                last_ind = """SELECT ask_price, bid_price, slow_stoch, cci, ma_1, ma_2, smarsi, qfl_base FROM trend_avg WHERE market='%s'""" % (market)
                                                                cursor.execute(last_ind)
                                                                last_ind = cursor.fetchone()

                                                                if side == 'buy':
                                                                    current_rate = last_ind[0]
                                                                else:
                                                                    current_rate = last_ind[1]
                                                                slow_avg = last_ind[2]
                                                                cci_avg = last_ind[3]
                                                                ma_1_prev_avg = last_ind[4]
                                                                ma_2_prev_avg = last_ind[5]
                                                                smarsi_avg = last_ind[6]
                                                                new_base_avg = last_ind[7]

                                                                #ВЫХОД ИЗ ЦИКЛА ЕСЛИ УСЛОВИЯ НЕ СООТВЕТСТВУЮТ
                                                                if side == 'buy' and ((current_rate != None and current_rate >= price_new) or (AVG_PRESET == "STOCH_CCI" and (AVG_USE_STOCH_C and slow_avg != None and slow_avg > AVG_STOCH_C_LONG_UP_LEVEL) or (AVG_USE_STOCH_S and slow_avg != None and slow_avg > AVG_STOCH_S_LONG_UP_LEVEL) or (AVG_USE_CCI and cci_avg != None and cci_avg > AVG_CCI_LONG_LEVEL)) or (AVG_PRESET == "CCI_CROSS" and ((AVG_CCI_CROSS_USE_PRICE == True and cci_avg != None and cci_avg > AVG_CCI_CROSS_LONG_LEVEL) or (AVG_CCI_CROSS_USE_PRICE == False and ((AVG_CCI_CROSS_METHOD == "crossover" and cci_avg != None and cci_avg < AVG_CCI_CROSS_LONG_LEVEL) or (AVG_CCI_CROSS_METHOD == "crossunder" and cci_avg != None and cci_avg > AVG_CCI_CROSS_LONG_LEVEL))))) or (AVG_PRESET == "MA_CROSS" and ma_1_prev_avg != None and ma_2_prev_avg != None and ma_1_prev_avg > ma_2_prev_avg) or (AVG_PRESET == "RSI_SMARSI" and smarsi_avg != None and smarsi_avg > AVG_SMARSI_CROSS_LONG_UP_LEVEL) or (AVG_PRESET == "MIDAS" and not new_base_avg)) or \
                                                                        side == 'sell' and ((current_rate != None and current_rate <= price_new) or (AVG_PRESET == "STOCH_CCI" and (AVG_USE_STOCH_C and slow_avg != None and slow_avg < AVG_STOCH_C_SHORT_LOW_LEVEL) or (AVG_USE_STOCH_S and slow_avg != None and slow_avg < AVG_STOCH_S_SHORT_LOW_LEVEL) or (AVG_USE_CCI and cci_avg != None and cci_avg < AVG_CCI_SHORT_LEVEL)) or (AVG_PRESET == "CCI_CROSS" and ((AVG_CCI_CROSS_USE_PRICE == True and cci_avg != None and cci_avg < AVG_CCI_CROSS_SHORT_LEVEL) or (AVG_CCI_CROSS_USE_PRICE == False and ((AVG_CCI_CROSS_METHOD == "crossover" and cci_avg != None and cci_avg > AVG_CCI_CROSS_SHORT_LEVEL) or (AVG_CCI_CROSS_METHOD == "crossunder" and cci_avg != None and cci_avg < AVG_CCI_CROSS_SHORT_LEVEL))))) or (AVG_PRESET == "MA_CROSS" and ma_1_prev_avg != None and ma_2_prev_avg != None and ma_1_prev_avg < ma_2_prev_avg) or (AVG_PRESET == "RSI_SMARSI" and smarsi_avg != None and smarsi_avg < AVG_SMARSI_CROSS_SHORT_LOW_LEVEL) or (AVG_PRESET == "MIDAS" and not new_base_avg)):
                                                                    ff = True
                                                            if ff == True:
                                                                break


                                                        # вышли из цикла проверки усреднения
                                                        # else:
                                                        #     print('ПРОБУЕМ УСРЕДНИТЬ, ЖДЕМ 10 сек')
                                                        #     await asyncio.sleep(10)
                                                        #     await create_limit(market, side, global_strategy, 1, price_new, "avg")
                                                    else:
                                                        if margin_flag == 0:
                                                            if ENTRY_BY_INDICATORS == True and USE_ENTRY_MARGIN == True:
                                                                log(market, '%s' % LANGUAGES[LANG]["log_bad_margin"])
                                                            if USE_TELEGRAM:
                                                                log(market, '%s' % LANGUAGES[LANG]["log_telegram"])
                                                                try:
                                                                    send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo, '✅ ' + LANGUAGES[LANG]["log_bad_margin"]))
                                                                    margin_flag = 1
                                                                except Exception as e:
                                                                    log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                        if orders_info[order]['order_filled']:
                                            #sell_count_long = if_buy_sell_count_filled(market, anti_side)

                                            balance = float(q['balance'])
                                            deal_number = get_deal_number(market)
                                            last_balance_q = """SELECT balance FROM orders WHERE market='%s' AND deal_number='%s' ORDER BY order_created DESC""" % (market, deal_number)
                                            cursor.execute(last_balance_q)
                                            last_balance = cursor.fetchone()[0]
                                            pnl = balance - last_balance
                                            base_order_balance = get_base_order_balance(market, side, deal_number)
                                            #print(side, deal_number, balance, last_balance, base_order_balance)
                                            deal_profit = balance - base_order_balance
                                            log_deal_length = deal_length(market, side)

                                            cursor.execute("""UPDATE orders SET order_filled=datetime(), order_price=:order_price, balance=:balance, profit=:profit WHERE order_id=:order_id""", {'order_id': order, 'order_price': order_info['price'], 'balance': balance, 'profit': deal_profit})
                                            conn.commit()
                                            cursor.execute("""UPDATE bo_order_check SET checked_date = 0 WHERE market=:market""", {'market': market})
                                            conn.commit()
                                            cursor.execute("""UPDATE counters SET counter_count = 0 WHERE counter_market=:counter_market""", {'counter_market': market})
                                            conn.commit()

                                            #cursor.execute("""UPDATE orders SET profit=:profit WHERE order_id=:order_id""", {'profit': deal_profit, 'order_id': order_info['id']})
                                            #conn.commit()

                                            new_ordr_total = config.get_value("bot", "orders_total")
                                            if ORDERS_TOTAL > new_ordr_total:
                                                cursor.execute("""UPDATE counters SET orders_total=:orders_total WHERE counter_market = :counter_market""", {'orders_total': new_ordr_total, 'counter_market': market})
                                                conn.commit()


                                            if EXIT_METHOD == 'profit_exit':
                                                if side == 'buy': log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_SELL_filled_long"], order_info['amount'], b_pair))
                                                else: log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_SELL_filled_short"], order_info['amount'], b_pair))

                                                if USE_TELEGRAM:
                                                    log(market, '%s' % LANGUAGES[LANG]["log_telegram"])
                                                    try:
                                                        send_msg("{}\n{}\n{}\n{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})',
                                                            '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo,
                                                            '✅ ' + LANGUAGES[LANG]["telegram_close_position"]  + ' ' + LANGUAGES[LANG]["telegram_for"] + ' ' + str(order_info['price']),
                                                            '💰 ' + LANGUAGES[LANG]["log_free_balance"] + ' ' + str(round(balance, 2)) + ' ' + q_pair,
                                                            '💵 ' + LANGUAGES[LANG]["telegram_deal_profit"] + ' ' + str(round(deal_profit, 2)) + ' ' + q_pair,
                                                            '📣 ' + log_deal_length))
                                                    except Exception as e:
                                                        log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                            else:
                                                log(market, '%s' % LANGUAGES[LANG]["log_telegram"])

                                                if orders_info[order]['squeeze'] == 1:
                                                    if side == 'buy': log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_SQUEEZE_filled_long"], order_info['amount'], b_pair))
                                                    else: log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_SQUEEZE_filled_short"], order_info['amount'], b_pair))
                                                    msg = LANGUAGES[LANG]["telegram_close_position"]

                                                if orders_info[order]['squeeze'] == 0:
                                                    if side == 'buy': log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_filled_long"], order_info['amount'], b_pair))
                                                    else: log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_filled_short"], order_info['amount'], b_pair))
                                                    msg = LANGUAGES[LANG]["telegram_close_position"]

                                                if orders_info[order]['stop_loss'] == 1:
                                                    if side == 'buy': log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_STOP_filled_long"], order_info['amount'], b_pair))
                                                    else: log(market, '%s %s %s.' % (LANGUAGES[LANG]["log_order_STOP_filled_short"], order_info['amount'], b_pair))
                                                    msg = LANGUAGES[LANG]["telegram_stop_loss_filled"]
                                                    sell_order_q = """SELECT order_id FROM orders WHERE market='%s' AND order_side = '%s' AND stop_loss=0 AND order_filled IS NULL AND order_cancelled IS NULL ORDER BY order_created DESC LIMIT 1""" % (market, anti_side)
                                                    cursor.execute(sell_order_q)
                                                    anti_order = cursor.fetchone()
                                                    try:
                                                        response = await connector.cancel_order(anti_order[0], market)
                                                        if response:
                                                            cancel_order_id(anti_order[0])
                                                            #log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], unrealized_order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                    except Exception as e:
                                                        log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 111', type(e).__name__, str(e)))


                                                if USE_TELEGRAM:
                                                    try:
                                                        send_msg("{}\n{}\n{}\n{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})',
                                                            '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo,
                                                            '✅ ' + msg  + ' ' + LANGUAGES[LANG]["telegram_for"] + ' ' + str(order_info['price']),
                                                            '💰 ' + LANGUAGES[LANG]["log_free_balance"] + ' ' + str(round(balance, 2)) + ' ' + q_pair,
                                                            '💵 ' + LANGUAGES[LANG]["telegram_deal_profit"] + ' ' + str(round(deal_profit, 2)) + ' ' + q_pair,
                                                            '📣 ' + log_deal_length))
                                                    except Exception as e:
                                                        log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))


                                            tables = ['entry', 'avg', 'exit']
                                            for i in tables:
                                                #print(tables)
                                                record_trend(market=market, table='trend_'+str(i), trend=0, flag='0', ask_price=current_ask, bid_price=current_bid, macdhist_1=0, macdhist_2=0, macdhist_3=0, macdhist_4=0, fast_stoch=0, slow_stoch=0, cci=0, ema200=0, rsi=0, smarsi=0, atr=0, efi=0, ma_1=0, ma_2=0, upper=0, middle=0, lower=0, fast_global=0, slow_global=0, qfl_result=0, qfl_base=0)

                                            for unrealized_order in orders_info:
                                                #print(orders_info[unrealized_order]['order_id'])
                                                if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                    try:
                                                        response = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                        if response:
                                                            cancel_order_id(orders_info[unrealized_order]['order_id'])
                                                            #log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], unrealized_order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                    except Exception as e:
                                                        c = True#log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 03', type(e).__name__, str(e)))
                                                        return

                                            if state["needed_stop_with_take_profit"].get():
                                                avg_market = state["selected_coin"].get()
                                                if market == avg_market or len(config.get_value("bot", "base_coin").replace(' ', '').split(',')) < 2:
                                                    if USE_TELEGRAM:
                                                        try:
                                                            send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '📟 ' + str(date.strftime("%d-%m-%Y %H:%M")) + ' 👉 ' + market + ' ' + algo, '✅ ' + LANGUAGES[LANG]["the_bot_stopped"]))
                                                        except Exception as e:
                                                            log('%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))

                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response:
                                                                    cancel_order_id(orders_info[unrealized_order]['order_id'])
                                                                    #log(market, '%s %s %s' % (LANGUAGES[LANG]["log_order"], unrealized_order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                            except Exception as e:
                                                                c = True#log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 04', type(e).__name__, str(e)))
                                                    state["fixed_profit"] = True

                                        # else:
                                        #     is_partially_filled = False
                                        #     try:
                                        #         current_order_info = await connector.get_order(orders_info[order]['order_id'], market)
                                        #     except Exception as e:
                                        #         log(market, '%s: %s %s' % ('GET ORDERS ERROR 03', type(e).__name__, str(e)))
                                        #
                                        #     if current_order_info['remaining']:
                                        #         current_remaining = float(current_order_info['remaining'])
                                        #     else:
                                        #         current_remaining = 0
                                        #
                                        #     if current_remaining != float(current_order_info['amount']) and current_order_info['status'] == 'open':
                                        #         is_partially_filled = True
                                        #
                                        #     # if order_info['status'] != 'canceled':
                                        #     #     log(market, LANGUAGES[LANG]["log_remaining_fix_value"], current_order_info['amount'], LANGUAGES[LANG]["log_remaining_remain"], current_remaining)
                                        #
                                        #     if is_partially_filled:
                                        #         response_flag = False
                                        #         # отменяем частично исполненный фикс
                                        #         try:
                                        #             response = await connector.cancel_order(order, market)
                                        #             cancel_order_id(order)
                                        #             log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                        #             response_flag = True
                                        #         except Exception as e:
                                        #             response_flag = False
                                        #             log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 05', type(e).__name__, str(e)))
                                        #
                                        #         if response_flag == True:
                                        #             # запускаем маркет-ордер на продажу остатка в размере current_order_info['remaining']
                                        #             log(market, "%s %s %s" % (LANGUAGES[LANG]["log_remaining_market_long"], current_remaining, b_pair))
                                        #             try:
                                        #                 await create_market(market=market, side=anti_side, global_strategy=global_strategy, remaining_amount=current_remaining, reason='sell_remaining')
                                        #             except Exception as e:
                                        #                 log(market, '%s: %s %s' % ('CREATE MARKET ORDER ERROR 01', type(e).__name__, str(e)))
                                        #             sell_remaining = True

                                    sell_orders_q = """SELECT order_id FROM orders WHERE market='%s' AND order_side='%s' AND order_filled IS NULL AND order_cancelled IS NULL""" % (market, anti_side)
                                    cursor.execute(sell_orders_q)
                                    sell_order = cursor.fetchone()

                                    if sell_order:
                                        sell_order_price_q = """SELECT order_price FROM orders WHERE order_id='%s'""" % (sell_order[0])
                                        cursor.execute(sell_order_price_q)
                                        sell_order_price = cursor.fetchone()[0]

                                    # ПОДТЯЖКА ОРДЕРОВ
                                    if not sell_order and STEP_ONE > 0.01 and orders_info[order]['order_side'] == side:
                                        #log(market, "%s" % LANGUAGES[LANG]["log_check_up_long"])
                                        get_base_order = get_base_order_state(market, get_deal_number(market))

                                        if ENTRY_PRESET == 'MIDAS':
                                            new_qfl = ind['qfl_result']
                                            new_base = ind['qfl_base']
                                            flag = False
                                            # берем из БД QFL и базу, если они есть
                                            old_qfl_base = """SELECT qfl_result, qfl_base FROM trend_entry WHERE market='%s'""" % (market)
                                            cursor.execute(old_qfl_base)
                                            result = cursor.fetchall()
                                            if not result or result[0] == None:
                                                old_qfl = 0
                                                old_base = 0
                                            else:
                                                old_qfl = result[0][0]
                                                old_base = result[0][1]
                                        else:
                                            if side == 'buy':
                                                max_order_q = """SELECT max(order_price) FROM orders WHERE market='%s' AND order_side='%s' AND order_filled IS NULL AND order_cancelled IS NULL""" % (market, side)
                                                cursor.execute(max_order_q)
                                                max_1 = cursor.fetchone()[0]
                                                old_rate = max_1 * (1 + STEP_ONE / 100)
                                            else:
                                                min_order_q = """SELECT min(order_price) FROM orders WHERE market='%s' AND order_side='%s' AND order_filled IS NULL AND order_cancelled IS NULL""" % (market, side)
                                                cursor.execute(min_order_q)
                                                min_1 = cursor.fetchone()[0]
                                                old_rate = min_1 / (1 + STEP_ONE / 100)

                                        if get_base_order != 0:#ЕСЛИ БО НЕ ВЫПОЛНЕН
                                            if (ENTRY_PRESET != 'MIDAS' and STEP_ONE > 0.01 and ((side == 'buy' and current_price > old_rate * (1 + LIFT_STEP / 100)) or (side == 'sell' and current_price < old_rate / (1 + LIFT_STEP / 100)))) or ((ENTRY_PRESET == 'MIDAS' and old_qfl == 'buy' and new_base > old_base and new_qfl and new_qfl == 'buy') or (ENTRY_PRESET == 'MIDAS' and old_qfl == 'sell' and new_qfl and new_base < old_base and new_qfl == 'sell')):
                                                response_cancel = False
                                                for order in orders_info:
                                                    if order_info['remaining'] == order_info['amount'] and order_info['status'] == 'open':
                                                        if ENTRY_PRESET == 'MIDAS': log(market, LANGUAGES[LANG]["log_orders_new_qfl"], orders_info[order]['order_amount'])
                                                        else: log(market, LANGUAGES[LANG]["log_orders_up_long"], orders_info[order]['order_amount'])
                                                        try:
                                                            response_cancel = await connector.cancel_order(order, market)
                                                            if response_cancel:
                                                                cancel_order_id(order)
                                                                log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                        except Exception as e:
                                                            c = True#log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 06', type(e).__name__, str(e)))
                                                if response_cancel and ENTRY_PRESET == 'MIDAS':
                                                    record_trend(market=market, table="trend_entry", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=0)




                                    # STOP-LOSS ВЫСТАВЛЯЕМ ТОЛЬКО ЕСЛИ ВСЕ УСРЕДНЕНИЯ ВЫПОЛНЕНЫ И В БД НЕТ НЕИСПОЛНЕННЫХ СТОП-ОРДЕРОВ ПО ПАРЕ
                                    if len(q) > 1 and not_filled_buy != None and sell_count == 0:
                                        if EXIT_STOP_LOSS_LEVEL != 0 and EXIT_STOP_LOSS_LEVEL != 111:
                                            if (side == 'buy' and current_price < pos_average - pos_average * EXIT_STOP_LOSS_LEVEL / 100) or (side == 'sell' and current_price > pos_average + pos_average * EXIT_STOP_LOSS_LEVEL / 100):
                                                log(market, "%s" % (LANGUAGES[LANG]["log_exit_stop_loss_allows"]))

                                                # ТУТ ВЫСТАВЛЯЕМ СТОП-ЛОСС ПО МАРКЕТУ
                                                try:
                                                    await create_market(market=market, side=anti_side, global_strategy=global_strategy, remaining_amount=pos_amount, reason='stop_loss')
                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('CREATE MARKET ORDER ERROR 02', type(e).__name__, str(e)))

                                                # ТУТ ОТМЕНЯЕМ ЛИМИТНЫЙ ФИКС, ЕСЛИ ОН ЕСТЬ
                                                for order in orders_info:
                                                    if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                        try:
                                                            response = await connector.cancel_order(order, market)
                                                            if response:
                                                                cancel_order_id(order)
                                                                log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], order, LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                        except Exception as e:
                                                            log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 07', type(e).__name__, str(e)))

                                                        break
                                                    break

                                        #ЛОГИКА ВЫСТАВЛЕНИЯ СТОПА ЗА ЭКСТРЕМУМЫ. ВЫСТАВЛЯЕМ ЕСЛИ В БД НЕТ НЕЗАПОЛНЕННОГО СТОПА
                                        stop_order_id = get_open_stop_order(market, anti_side, get_deal_number(market))

                                        if EXIT_STOP_LOSS_LEVEL == 111 and stop_order_id == 0:

                                            if side == 'buy':
                                                stop_loss_price = stop_loss_price_long
                                                if stop_loss_price > current_price:
                                                    stop_loss_price = pos_average / (1 + 25 / leverage / 100)
                                            else:
                                                stop_loss_price = stop_loss_price_short
                                                if stop_loss_price < current_price:
                                                    stop_loss_price = pos_average * (1 + 25 / leverage / 100)


                                            try:
                                                # запускаем лимитные ордеры
                                                await create_limit(market=market, side=anti_side, global_strategy=global_strategy, immediate=0, price_level=stop_loss_price, remaining_amount=pos_amount, reason='stop_loss')
                                            except Exception as e:
                                                log(market, '%s: %s %s' % ('CREATE STOP-LOSS ORDER ERROR 01', type(e).__name__, str(e)))
                                                if USE_TELEGRAM:
                                                    try:
                                                        send_msg("{}\n{}\n{}".format(EXCHANGE + ' ' + f'({MY_NOTE})', '⛔ ' + str(date.strftime("%d-%m-%Y %H:%M")) + LANGUAGES[LANG]["log_stopped"], '⚠ ' + 'CREATE STOP-LOSS ORDER ERROR 01 ' + type(e).__name__ + str(e)))
                                                    except Exception as e:
                                                        log(market, '%s: %s %s' % ('TELEGRAM MESSAGE CANNOT BE SENT', type(e).__name__, str(e)))
                                                state["needed_stop"] = True
                                                state["fixed_profit"] = True
                                                await asyncio.sleep(0.1)
                                                return

                                    # ЛОГИКА ВЫХОДА
                                    if EXIT_METHOD == 'profit_exit':
                                        if sell_order:
                                            exit_price = sell_order_price
                                        else:
                                            if side == 'buy':
                                                exit_price = 0
                                            else:
                                                exit_price = 10000000

                                    if BACK_PROFIT != 0:
                                        bp = get_bp(BACK_PROFIT, sell_count)
                                    else:
                                        bp = 1

                                    if EXIT_METHOD == 'indicators_exit':
                                        if side == 'buy':
                                            exit_price = round(pos_average + pos_average * EXIT_PROFIT_LEVEL / bp / 100, pricePrecision)
                                        else:
                                            exit_price = round(pos_average - pos_average * EXIT_PROFIT_LEVEL / bp / 100, pricePrecision)


                                    if len(q) > 1 and ((side == 'buy' and current_price > exit_price) or (side == 'sell' and current_price < exit_price)):
                                        f = False
                                        if TIME_SLEEP > 60:
                                            TIME_SLEEP = 60
                                        log(market, "%s %s. %s %s. %s %s (%s %s)" % (LANGUAGES[LANG]["log_close_price"], exit_price, LANGUAGES[LANG]["log_current_price"], current_price, LANGUAGES[LANG]["average_price_delta"], roe_pcnt, pnl, q_pair))

                                        if EXIT_METHOD == 'profit_exit':
                                            log(market, LANGUAGES[LANG]["log_closing_position"], algo)

                                        if EXIT_METHOD == 'indicators_exit':
                                            # for unrealized_order in orders_info:
                                            #     if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                            #         try:
                                            #             response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                            #             if response_cancel:
                                            #                 log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                            #                 cancel_order_id(order)
                                            #                 f = True
                                            #         except Exception as e:
                                            #             log(market, '%s: %s %s' % ('CANCEL ORDER ERROR 09', type(e).__name__, str(e)))

                                            if EXIT_CCI_CROSS_USE_PRICE == True and EXIT_PRESET == "CCI_CROSS":
                                                add_text = " + price"
                                            else:
                                                add_text = ""
                                            log(market, "%s: %s%s (%s)" % (LANGUAGES[LANG]["log_exit_preset_chosen"], EXIT_PRESET, add_text, EXIT_TF))


                                            global_ind = await get_indicators_advice(config, market, GLOBAL_TF, 'exit')
                                            ind = await get_indicators_advice(config, market, EXIT_TF, 'exit')

                                            if side == 'buy':
                                                current_rate = current_bid
                                            else:
                                                current_rate = current_ask
                                            global_strategy = global_ind['trend']


                                            if EXIT_PRESET == "STOCH_CCI":
                                                STOCH_ALLOWS, CCI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_cci_answer(market, 'exit', side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], cci_3=ind['cci_3'], cci_2=ind['cci_2'], cci=ind['cci_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                if EXIT_USE_STOCH_C == True:
                                                    log(market, "%s %s. %s %s: %s %.3f, %s %.3f" % (LANGUAGES[LANG]["log_current_price"], LANGUAGES[LANG]["log_stoch_allows_exit"], EXIT_TF, text_stoch, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if EXIT_USE_CCI == True:
                                                    log(market, "%s %s. %s %s: (%.3f, %.3f, %.3f)" % (LANGUAGES[LANG]["log_current_price"], LANGUAGES[LANG]["log_stoch_allows_exit"], "CCI", EXIT_TF, ind['cci_3'], ind['cci_2'], ind['cci_1']))
                                                if USE_GLOBAL_STOCH == True:
                                                    log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if STOCH_ALLOWS and CCI_ALLOWS and GLOBAL_STOCH_ALLOWS:
                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response_cancel:
                                                                    cancel_order_id(order)
                                                                    log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                    f = True
                                                            except Exception as e:
                                                                flag = True

                                            elif EXIT_PRESET == "STOCH_RSI":
                                                STOCH_ALLOWS, RSI_ALLOWS, GLOBAL_STOCH_ALLOWS = get_stoch_rsi_answer(market, 'exit', side, slow_stoch=ind['slow'], fast_stoch=ind['fast'], rsi_3=ind['rsi_3'], rsi_2=ind['rsi_2'], rsi=ind['rsi_1'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                if EXIT_USE_STOCH_S == True:
                                                    log(market, "%s %s. %s %s: %s %.3f, %s %.3f" % (LANGUAGES[LANG]["log_current_price"], LANGUAGES[LANG]["log_stoch_allows_exit"], EXIT_TF, text_stoch, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if EXIT_USE_RSI == True:
                                                    log(market, "%s %s. %s %s: (%.3f, %.3f, %.3f)" % (LANGUAGES[LANG]["log_current_price"], LANGUAGES[LANG]["log_stoch_allows_exit"], "RSI", EXIT_TF, ind['rsi_3'], ind['rsi_2'], ind['rsi_1']))
                                                if USE_GLOBAL_STOCH == True:
                                                    log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if STOCH_ALLOWS and RSI_ALLOWS and GLOBAL_STOCH_ALLOWS:
                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response_cancel:
                                                                    cancel_order_id(order)
                                                                    log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                    f = True
                                                            except Exception as e:
                                                                flag = True


                                            elif EXIT_PRESET == "CCI_CROSS":
                                                CCI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_cci_cross_answer(market, 'exit', side, current_price=current_rate, cci=ind['cci_1'], cci_2=ind['cci_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                if CCI_CROSS_ALLOWS:
                                                    log(market, "%s%s %s" % (EXIT_PRESET, add_text, LANGUAGES[LANG]["log_cross_"+side]))
                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response_cancel:
                                                                    cancel_order_id(order)
                                                                    log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                    f = True
                                                            except Exception as e:
                                                                flag = True

                                            elif EXIT_PRESET == "MA_CROSS":
                                                MA_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_ma_cross_answer(market, 'exit', side, current_price=current_rate, ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], ma_1_prev=ind['ma_1_2'], ma_2_prev=ind['ma_2_2'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                if USE_GLOBAL_STOCH == True:
                                                    log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if MA_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS:
                                                    log(market, "%s %s" % (EXIT_PRESET, LANGUAGES[LANG]["log_cross_"+side]))
                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response_cancel:
                                                                    cancel_order_id(order)
                                                                    log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                    f = True
                                                            except Exception as e:
                                                                flag = True

                                            elif EXIT_PRESET == "RSI_SMARSI":
                                                RSI_SMARSI_CROSS_ALLOWS, GLOBAL_STOCH_ALLOWS = get_rsi_smarsi_cross_answer(market, 'exit', side, current_price=current_rate, rsi=ind['rsi_1'], smarsi=ind['smarsi'], fast_global=global_ind['fast'], slow_global=global_ind['slow'])

                                                if USE_GLOBAL_STOCH == True:
                                                    log(market, "%s %s: %s %0.3f, %s: %0.3f" % ("GLOBAL_STOCH", GLOBAL_TF, LANGUAGES[LANG]["fast_STOCH"], global_ind['fast'], LANGUAGES[LANG]["slow_STOCH"], global_ind['slow']))
                                                if RSI_SMARSI_CROSS_ALLOWS and GLOBAL_STOCH_ALLOWS:
                                                    log(market, "%s %s" % (EXIT_PRESET, LANGUAGES[LANG]["log_cross_"+side]))
                                                    for unrealized_order in orders_info:
                                                        if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                            try:
                                                                response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                                if response_cancel:
                                                                    cancel_order_id(order)
                                                                    log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                    f = True
                                                            except Exception as e:
                                                                flag = True

                                            elif EXIT_PRESET == 'MIDAS' and ind['qfl_result'] == anti_side:
                                                for unrealized_order in orders_info:
                                                    if open_orders_count(market, side) > 0 or open_orders_count(market, anti_side) > 0:
                                                        try:
                                                            response_cancel = await connector.cancel_order(orders_info[unrealized_order]['order_id'], market)
                                                            if response_cancel:
                                                                log(market, "%s %s %s" % (LANGUAGES[LANG]["log_order"], orders_info[unrealized_order]['order_id'], LANGUAGES[LANG]["log_order_market_canceled_DB"]))
                                                                cancel_order_id(orders_info[unrealized_order]['order_id'])
                                                                f = True
                                                        except Exception as e:
                                                            flag = True
                                            else:
                                                log(market, "%s %s %s %s" % (LANGUAGES[LANG]["log_no_signal_yet"], EXIT_PRESET, LANGUAGES[LANG]["log_for_closing"], algo))

                                            record_trend(market=market, table="trend_exit", trend=global_ind['trend'], flag="0", ask_price=current_ask, bid_price=current_bid, macdhist_1=ind['macd_h_1'], macdhist_2=ind['macd_h_2'], macdhist_3=ind['macd_h_3'], macdhist_4=ind['macd_h_4'], fast_stoch=ind['fast'], slow_stoch=ind['slow'], cci=ind['cci_1'], ema200=ind['ema200'], rsi=ind['rsi_1'], smarsi=ind['smarsi'], atr=ind['atr'], efi=ind['efi'], ma_1=ind['ma_1_1'], ma_2=ind['ma_2_1'], upper=ind['upper'], middle=ind['middle'], lower=ind['lower'], fast_global=global_ind['fast'], slow_global=global_ind['slow'], qfl_result=0, qfl_base=0)

                                            if f:
                                                log(market, "%s %s. %s %s" % (LANGUAGES[LANG]["log_signal_found"], EXIT_PRESET, LANGUAGES[LANG]["log_closing_position"], algo))
                                                try:
                                                    await create_market(market=market, side=anti_side, global_strategy=global_strategy, remaining_amount=abs(pos_amount), reason='exit')
                                                except Exception as e:
                                                    log(market, '%s: %s %s' % ('CREATE MARKET ORDER ERROR 03', type(e).__name__, str(e)))
                                                break

                sell_count = get_sell_counter(market)
                deal_number = get_deal_number(market)
                get_base_order = get_base_order_state(market, deal_number)

                filled_fix = True
                if q and len(q) > 1:
                    cursor.execute("""SELECT order_filled FROM orders WHERE market=:market AND deal_number=:deal_number AND order_side=:side AND order_filled IS NOT NULL ORDER BY order_created DESC LIMIT 1""", {'market': market, 'deal_number': deal_number, 'side': side})
                    filled_fix = cursor.fetchone()

                if ACTIVE_ORDERS == 0:
                    if (state["manual_averaging"].get() or state["manual_sell"].get()) or (STEP_ONE < 0.011 and sell_count == 0 and (get_base_order != 0 and filled_fix == None)):
                        await asyncio.sleep(5)
                    # elif sell_count == 0 and filled_buy == None and get_base_order == 0 and STOP_IF_NO_BALANCE == False:
                    #     await asyncio.sleep(TIME_SLEEP_KOEFF * int(config.get_value("bot", "time_sleep")))
                    else:
                        await asyncio.sleep(TIME_SLEEP)
                else:
                    await asyncio.sleep(TIME_SLEEP)

            except Exception as e:
                if str(e) != "local variable 'pricePrecision' referenced before assignment":
                    log(market, '%s: %s %s' % ('BOT ERROR 01', type(e).__name__, str(e)))

    async def tasks(thread, state):
        create_tables()

        while not thread.stopped():
            now = datetime.now()
            if now < expire_UTC:
                await bot(thread, state)
            else:
                log('Лицензия истекла. Обратитесь в телеграм разработчика @frankie8379')
                break
        else:
            print('бот остановлен')



    asyncio.set_event_loop(loop)
    loop.run_until_complete(tasks(thread, state))
