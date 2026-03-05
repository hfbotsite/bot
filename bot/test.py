import os
import re
import math
import time
import json
import hmac, hashlib
import sqlite3
from bot.kernel import Connector
from bot.defines import LANGUAGES
import asyncio

def test(thread, config, logger, loop):
    conn = sqlite3.connect('bot.db', check_same_thread=False)
    cursor = conn.cursor()
    connector = Connector()

    def log(*args):
        logger.info(" ".join([str(x) for x in args]))



    async def bot(thread):
        EXCHANGE = 'bybit'  # config.get_value("bot", "exchange")
        LANG = config.get_value("bot", "language")
        BASE_COIN = config.get_value("bot", "base_coin")
        QUOTE_COIN = config.get_value("bot", "quote_coin")
        base_coins = BASE_COIN.replace(' ', '').split(',')
        SQUEEZE_PROFIT = config.get_value("exit", "squeeze_profit")
        LEVERAGE = config.get_value("bot", "leverage")
        # LEVERAGE_ARRAY = LEVERAGES.replace(' ', '').split(',')
        PERCENT_OR_AMOUNT = True  # config.get_value("bot", "percent_or_amount")

        BO_AMOUNT = config.get_value("bot", "bo_amount")
        SO_AMOUNT = config.get_value("bot", "so_amount")
        ACTIVE_ORDERS = config.get_value("bot", "active_orders")
        MARTINGALE = config.get_value("bot", "martingale")
        depo_percent = config.get_value("bot", "depo")

        STEP_ONE = 0
        H_L_PERCENT = 0#config.get_value("entry_preset_midas", "h_l_percent")

        N = len(base_coins)
        pair = [base_coins[0], QUOTE_COIN]
        market = pair[0] + '/' + pair[1]

        margin_mode = config.get_value("bot", "margin_mode")

        def count(cur, table, market):
            count_q = """
            SELECT
                COUNT(*)
            FROM
                '%s'
            WHERE
                market='%s'
            """ % (table, market)
            if cur == 'candles':
                ticks_cursor.execute(count_q)
                result = ticks_cursor.fetchone()
                ticks_conn.commit()
            else:
                cursor.execute(count_q)
                result = cursor.fetchone()
                conn.commit()
            return result

        if not thread.stopped():
            ORDERS_TOTAL = config.get_value("bot", "orders_total")
            if ORDERS_TOTAL < 2:
                log("orders_total parameter in config.toml file must be > 1 to test the grid prices")
            else:
                # try:
                #     if EXCHANGE == 'kucoinfutures':
                #         await connector.configure(config, market + ':' + market.split('/')[1])
                #
                #     else:
                #         await connector.configure(config, market)
                #
                #     q = await connector.get_balance(base_coins[0], QUOTE_COIN, config)  # Берем данные по позе: balance, pnl, pos_average, leverage, pos_amount, pos_cost, pos_id, roe_pcnt
                # except Exception as e:
                #     log(market, '%s: %s %s' % ('GET BALANCE ERROR 01', type(e).__name__, str(e)))
                #
                #
                # balance = float(q['balance'])

                try:
                    if EXCHANGE == 'kucoinfutures':
                        await connector.configure(config, market + ':' + market.split('/')[1])
                    else:
                        await connector.configure(config, market)
                except Exception as e:
                    log(market, '%s: %s %s' % ('CONFIGURE ERROR 01', type(e).__name__, str(e)))

                try:
                    q = await connector.get_balance(pair[0], pair[1], config)  # Берем данные по позе: balance, pnl, pos_average, leverage, pos_amount, pos_cost, pos_id, roe_pcnt
                except Exception as e:
                    log(market, '%s: %s %s' % ('GET BALANCE ERROR 01', type(e).__name__, str(e)))
                    await asyncio.sleep(10)
                    return

                balance = float(q['balance'])

                if PERCENT_OR_AMOUNT == True:

                    CAN_SPEND = float(LEVERAGE) * (balance * depo_percent / 100) / N
                    BO_AMOUNT = CAN_SPEND * BO_AMOUNT / 100
                    SO_AMOUNT = CAN_SPEND - BO_AMOUNT
                else:
                    CAN_SPEND = LEVERAGE * depo_percent / N


                COIN_1 = base_coins[0]
                COIN_2 = QUOTE_COIN


                STEP_ONE = config.get_value("bot", "first_step")
                OVERLAP_PRICE = config.get_value("bot", "range_cover")


                FIRST_CO_KOEFF = config.get_value("bot", "first_so_coeff")
                DYNAMIC_CO_KOEFF = config.get_value("bot", "dynamic_so_coeff")


                ask, bid = await connector.get_ask_bid(market)
                # print(ask, bid)
                if EXCHANGE == 'binance':
                    current_ask = ask
                    current_bid = current_ask
                else:
                    current_ask = ask
                    current_bid = bid



                amountPrecision = None
                pricePrecision = None
                amountLimit = None
                try:
                    if count('bot', 'limits', market) == None or int(count('bot', 'limits', market)[0]) < 1:
                        amountPrecision, pricePrecision, amountLimit = connector.get_precision(market)
                        cursor.execute(
                            """INSERT INTO limits(market, amount_precision, price_precision, amount_limit) values(:market, :amount_precision, :price_precision, :amount_limit)""",
                            {'market': market, 'amount_precision': amountPrecision, 'price_precision': pricePrecision, 'amount_limit': amountLimit})
                        conn.commit()
                    else:
                        cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % market)
                        precisions = cursor.fetchall()[0]
                        amountPrecision, pricePrecision, amountLimit = precisions
                except Exception as e:
                    f = True#log(market, '%s: %s %s' % ('ERROR 01', type(e).__name__, str(e)))



                long_price_0 = current_ask - (current_ask * ((STEP_ONE + H_L_PERCENT) / 100))
                long_price_1 = long_price_0 - long_price_0 * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)

                short_price_0 = current_bid + (current_bid * ((STEP_ONE + H_L_PERCENT) / 100))
                short_price_1 = short_price_0 + short_price_0 * (FIRST_CO_KOEFF * OVERLAP_PRICE / 100)

                long_p_1 = round(long_price_1, pricePrecision)
                short_p_1 = round(short_price_1, pricePrecision)
                long_p = []
                short_p = []

                #LONG
                for i in range(3, ORDERS_TOTAL + 1):
                    long_a = long_price_1 - long_price_1 * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** i) / 100
                    long_price_1 = long_a
                    long_p.append(round(long_a, pricePrecision))

                #SHORT
                for i in range(3, ORDERS_TOTAL + 1):
                    short_a = short_price_1 + short_price_1 * (OVERLAP_PRICE * DYNAMIC_CO_KOEFF ** i) / 100
                    short_price_1 = short_a
                    short_p.append(round(short_a, pricePrecision))

                long_price = [long_price_0] + [long_p_1] + long_p
                short_price = [short_price_0] + [short_p_1] + short_p


                canspend_0 = BO_AMOUNT
                canspend_1 = SO_AMOUNT / ((1 - MARTINGALE ** (ORDERS_TOTAL - 1)) / (1 - MARTINGALE))
                c_1 = canspend_1

                canspend_so = []
                for i in range(3, ORDERS_TOTAL + 1):
                    c = canspend_1 * MARTINGALE
                    canspend_1 = c
                    canspend_so.append(c)
                canspend = [canspend_0] + [c_1] + canspend_so

                long_amount = []
                for i in range(len(long_price)):
                    long_amount.append(round(canspend[i] / long_price[i], amountPrecision))

                short_amount = []
                for i in range(len(short_price)):
                    short_amount.append(round(canspend[i] / short_price[i], amountPrecision))




                log("MARKET =", market)
                log("-----------------")
                log("BALANCE =", balance, QUOTE_COIN)
                log("CAN_SPEND =", CAN_SPEND/float(LEVERAGE), QUOTE_COIN)
                log("RANGE_COVER =", OVERLAP_PRICE)
                log("ORDERS_TOTAL =", ORDERS_TOTAL)
                log("MARTINGALE =", MARTINGALE)
                log("LEVERAGE =", LEVERAGE)


                long_order_amount = []
                long_canbuy = []
                long_spend_btc = []

                log("-----------------")
                log("ALGORITHM =", 'LONG')
                log("")
                log("        %s  %s    %s (%s)  %s (%s)  %s (%s)  %s" % (LANGUAGES[LANG]["test_buy_price"], "      %", LANGUAGES[LANG]["test_spent"], COIN_2, LANGUAGES[LANG]["test_received"], COIN_1, LANGUAGES[LANG]["test_received"], COIN_2, LANGUAGES[LANG]["test_liquidation"]))

                #LONG
                long_d = []
                for i in range(ORDERS_TOTAL):
                    if i < ORDERS_TOTAL - 1:
                        long_d.append(round(((long_price[i] - long_price[0]) / long_price[0]) * 100, 2))
                    long_a = round(((long_price[ORDERS_TOTAL - 1] - long_price[0]) / long_price[0]) * 100, 2)
                long_delta = long_d + [long_a]

                for i in range(ORDERS_TOTAL):
                    long_canbuy.append(canspend[i] / long_price[i])
                    long_spend_btc.append(round((long_canbuy[i] * long_price[i]), 8))

                    long_order_spent = round(sum([i for i in long_spend_btc]), 8)
                    long_order_amount = round(sum([i for i in long_canbuy]), 8)

                    long_average_price = round(long_order_spent / long_order_amount, 8)
                    pnl = round(abs(((long_price[i] - long_average_price) / long_average_price) * 100 * (long_order_spent / float(LEVERAGE)) / float(LEVERAGE)), pricePrecision)

                    initial_margin = long_order_spent/float(LEVERAGE)
                    total_equity = balance -  N * initial_margin
                    if margin_mode == 'cross':
                        long_liquidation = round(long_average_price * (1 - (initial_margin + total_equity - long_order_spent) / (long_order_spent * float(LEVERAGE))), pricePrecision)
                    else:
                        long_liquidation = round(long_average_price * (1 - 1 / float(LEVERAGE)), pricePrecision)

                    log("[{:>2}]  {:>.4f}".format(i + 1, long_price[i]), "{:>7.2f}".format(long_delta[i]), "{:>10.2f}".format(round(long_order_spent/float(LEVERAGE), 8)), "{:>20.8f}".format(long_order_amount), "{:>18.4f}".format(long_order_spent), "{:>18.4f}".format(long_liquidation) if long_liquidation > 0 else "{:>18}".format('None'))


                log("")
                log(LANGUAGES[LANG]["test_var_average_long"], round(long_average_price, pricePrecision))

                if long_liquidation and long_liquidation > long_price[-1]:
                        log(LANGUAGES[LANG]["test_var_liquidation"])
                else:
                    log(LANGUAGES[LANG]["test_var_pnl"], -1*pnl, COIN_2, LANGUAGES[LANG]["test_or"], round(pnl/balance*100, pricePrecision), '%')





                log("")
                log("-----------------")
                log("ALGORITHM =", 'SHORT')
                log("")
                log("        %s  %s    %s (%s)  %s (%s)  %s (%s)  %s" % (LANGUAGES[LANG]["test_buy_price"], "      %", LANGUAGES[LANG]["test_spent"], COIN_2, LANGUAGES[LANG]["test_received"], COIN_1, LANGUAGES[LANG]["test_received"], COIN_2, LANGUAGES[LANG]["test_liquidation"]))


                short_order_amount = []
                short_canbuy = []
                short_spend_btc = []

                #SHORT
                short_d = []

                # for i in range(ORDERS_TOTAL):
                #     if i < ORDERS_TOTAL-1:
                #         short_d.append(round(abs(-(short_price[0] / short_price[i] - 1) * 100), 2))
                #     short_a = round(abs(-(short_price[0] / short_price[ORDERS_TOTAL-1] - 1) * 100), 2)
                # short_delta = short_d + [short_a]


                for i in range(ORDERS_TOTAL):
                    if i < ORDERS_TOTAL - 1:
                        short_d.append(round(((short_price[i] - short_price[0]) / short_price[0]) * 100, 2))
                    short_a = round(((short_price[ORDERS_TOTAL - 1] - short_price[0]) / short_price[0]) * 100, 2)
                short_delta = short_d + [short_a]

                # SHORT
                for i in range(ORDERS_TOTAL):
                    short_canbuy.append(canspend[i] / short_price[i])
                    short_spend_btc.append(round((short_canbuy[i] * short_price[i]), 8))

                    short_order_spent = round(sum([i for i in short_spend_btc]), 8)
                    short_order_amount = round(sum([i for i in short_canbuy]), 8)

                    short_average_price = round(short_order_spent / short_order_amount, 8)
                    pnl = round(abs(((short_price[i] - short_average_price) / short_average_price) * 100 * (short_order_spent/float(LEVERAGE)) / float(LEVERAGE)), pricePrecision)

                    initial_margin = short_order_spent/float(LEVERAGE)
                    total_equity = balance -  N * initial_margin

                    if margin_mode == 'cross':
                        short_liquidation = round(short_average_price * (1 + (initial_margin + total_equity - short_order_spent) / (short_order_spent * float(LEVERAGE))), pricePrecision)
                    else:
                        short_liquidation = round(short_average_price * (1 + 1 / float(LEVERAGE)), pricePrecision)

                    log("[{:>2}]  {:>.4f}".format(i + 1, short_price[i]), "{:>7.2f}".format(short_delta[i]), "{:>10.2f}".format(round(short_order_spent/float(LEVERAGE), 8)), "{:>20.8f}".format(short_order_amount), "{:>18.4f}".format(short_order_spent), "{:>18.4f}".format(short_liquidation if short_liquidation >0 else 0))

                short_average_price = round(short_order_spent / short_order_amount, 8)
                log("")
                log(LANGUAGES[LANG]["test_var_average_short"], round(short_average_price, pricePrecision))

                if short_liquidation and short_liquidation < short_price[-1]:
                        log(LANGUAGES[LANG]["test_var_liquidation"])
                else:
                    log(LANGUAGES[LANG]["test_var_pnl"], -1*pnl, COIN_2, LANGUAGES[LANG]["test_or"], round(pnl/balance*100, pricePrecision), '%')




        await asyncio.sleep(9000000000000)

    async def tasks(thread):
        while not thread.stopped():
            await bot(thread)
        else:
            print('бот остановлен')

    asyncio.set_event_loop(loop)
    loop.run_until_complete(tasks(thread))