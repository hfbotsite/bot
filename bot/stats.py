import re
import os
import sqlite3
from hfbot.defines import LANGUAGES
from hfbot.kernel import Connector

def stats(thread, config, logger):
    connector = Connector()
    connector.configure(config)
    
    def log(*args):
        logger.info(" ".join([str(x) for x in args]))
        
    lang = config.get_value("bot", "language")
    orders_total = config.get_value("bot", "orders_total")
    profit = config.get_value("bot", "profit_flat")
    conn = sqlite3.connect('hfbot.db')
    cursor = conn.cursor()
    file_path = r"hfbot.db"



    if os.stat(file_path).st_size == 0:
        print(LANGUAGES[lang]["statistics_are_not_available"])

    else:
        markets_q = """
            SELECT DISTINCT
              order_market
            FROM
              orders
        """
        cursor.execute(markets_q)
        MARKETS = cursor.fetchall()

        print(LANGUAGES[lang]["trade_statistics"])
            
        for market in MARKETS:
            baseCurrency = market[0].split('/')[0]
            quoteCurrency = market[0].split('/')[1]
            
            buy_count_long_q = """
              SELECT
                  COUNT(*)
              FROM
                  orders
              WHERE
                  order_market='%s'
                  AND order_type = 'buy'
                  AND algorithm = 'long'
                  AND order_filled IS NOT NULL
            """ % market
            cursor.execute(buy_count_long_q)
            buy_count_long = cursor.fetchone()[0]

            sell_count_short_q = """
              SELECT
                  COUNT(*)
              FROM
                  orders
              WHERE
                  order_market='%s'
                  AND order_type = 'sell'
                  AND algorithm = 'short'
                  AND order_filled IS NOT NULL
            """ % market
            cursor.execute(sell_count_short_q)
            sell_count_short = cursor.fetchone()[0]
                
            grow_q = """
              SELECT
                  grow_first
              FROM
                  orders
              WHERE
                  order_market='%s'
                  AND order_cancelled IS NULL
            """ % market
            cursor.execute(grow_q)
            grow_f = cursor.fetchone()[0]
            
            if buy_count_long > 0:
                if grow_f == "0":
                    
                    sell_count_long_q = """
                      SELECT
                          COUNT(*)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'long'
                          AND order_filled IS NOT NULL
                    """ % market
                    cursor.execute(sell_count_long_q)
                    sell_count_long = cursor.fetchone()[0]
                    
                    buy_o_spent_long_q = """
                      SELECT
                          SUM(order_spent)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'buy'
                          AND algorithm = 'long'
                          AND order_filled IS NOT NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(buy_o_spent_long_q)
                    buy_o_spent_long = cursor.fetchone()[0]

                    sell_o_spent_long_q = """
                      SELECT
                          SUM(order_spent)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'long'
                          AND order_filled IS NOT NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(sell_o_spent_long_q)
                    sell_o_spent_long = cursor.fetchone()[0]

                    
                    bought = round(buy_o_spent_long,8)
                    if sell_count_long > 0:
                        sold = round(sell_o_spent_long,8)
                    else:
                        sold = 0
                        
                    not_sold_yet_q = """
                      SELECT
                          order_spent
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'long'
                          AND order_filled IS NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(not_sold_yet_q)
                    row = cursor.fetchone()
                    
                    if row == None:
                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_long"], ")")
                        print(LANGUAGES[lang]["statistics_bought_long"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_sold_long"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["test_profit"], "{:.8f}".format(abs(sold - bought)), quoteCurrency)
                        print("")             
                    else:
                        not_sold_yet = row[0]
                        
                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_long"], ")")
                        print(LANGUAGES[lang]["statistics_bought_long"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_sold_long"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_if_will_sell_long"], "{:.8f}".format(abs(sold + not_sold_yet - bought)), quoteCurrency)
                        print("")
                        
                if grow_f == "1":
                    not_sold_yet_q = """
                      SELECT
                          order_spent
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'long'
                          AND order_filled IS NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(not_sold_yet_q)
                    row = cursor.fetchone()

                    sell_count_long_q = """
                      SELECT
                          COUNT(*)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'long'
                          AND order_filled IS NOT NULL
                    """ % market
                    cursor.execute(sell_count_long_q)
                    sell_count_long = cursor.fetchone()[0]
                    
                    amount_buy_long_q = """
                      SELECT
                          SUM(order_spent)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'buy'
                          AND algorithm = 'long'
                          AND order_filled IS NOT NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(amount_buy_long_q)
                    amount_buy_long = cursor.fetchone()[0]

                    if sell_count_long > 0:
                        amount_sell_long_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'sell'
                              AND algorithm = 'long'
                              AND order_cancelled IS NULL
                              AND order_filled IS NOT NULL
                        """ % market
                        cursor.execute(amount_sell_long_q)
                        amount_sell_long = cursor.fetchone()[0]
                    else:
                        amount_sell_long_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'sell'
                              AND algorithm = 'long'
                              AND order_cancelled IS NULL
                              AND order_filled IS NULL
                        """ % market
                        cursor.execute(amount_sell_long_q)
                        amount_sell_long = cursor.fetchone()[0]
                   
                    bought = round(amount_buy_long,8)
                    if sell_count_long > 0:
                        sold = round(amount_sell_long,8)
                    else:
                        sold = 0

                    if row == None:
                        price_sell_long_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'sell'
                              AND algorithm = 'long'
                              AND order_filled IS NOT NULL
                              AND order_cancelled IS NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_sell_long_q)
                        price_sell_long = cursor.fetchone()[0]

                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_long"], ")")
                        print(LANGUAGES[lang]["statistics_bought_long"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_sold_long"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["test_profit"], "{:.8f}".format(abs((bought - sold)/price_sell_long)), baseCurrency)
                        print("")

                    else:
                        not_sold_yet = row[0]

                        price_sell_long_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'sell'
                              AND algorithm = 'long'
                              AND order_filled IS NULL
                              AND order_cancelled IS NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_sell_long_q)
                        price_sell_long = cursor.fetchone()[0]

                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_long"], ")")
                        print(LANGUAGES[lang]["statistics_bought_long"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_sold_long"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_if_will_sell_long"], "{:.8f}".format(abs((bought - sold - not_sold_yet)/price_sell_long)), baseCurrency)
                        print("")
                        
            if sell_count_short > 0:                   
                buy_count_short_q = """
                  SELECT
                      COUNT(*)
                  FROM
                      orders
                  WHERE
                      order_market='%s'
                      AND order_type = 'buy'
                      AND algorithm = 'short'
                      AND order_filled IS NOT NULL
                      AND order_cancelled IS NULL
                """ % market
                cursor.execute(buy_count_short_q)
                buy_count_short = cursor.fetchone()[0]

                not_bought_yet_q = """
                  SELECT
                      order_spent
                  FROM
                      orders
                  WHERE
                      order_market='%s'
                      AND order_type = 'buy'
                      AND algorithm = 'short'
                      AND order_filled IS NULL
                      AND order_cancelled IS NULL
                """ % (market)
                cursor.execute(not_bought_yet_q)
                row = cursor.fetchone()

                if row == None:
                    amount_sell_short_q = """
                      SELECT
                          SUM(order_spent)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'short'
                          AND order_filled IS NOT NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(amount_sell_short_q)
                    amount_sell_short = cursor.fetchone()[0]

                    if buy_count_short > 0:
                        amount_buy_short_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_filled IS NOT NULL
                              AND order_cancelled IS NULL
                        """ % market
                        cursor.execute(amount_buy_short_q)
                        amount_buy_short = cursor.fetchone()[0]

                        price_buy_short_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_filled IS NOT NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_buy_short_q)
                        price_buy_short = cursor.fetchone()[0]
                    
                    else:
                        amount_buy_short_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_cancelled IS NULL
                              AND order_filled IS NULL
                        """ % market
                        cursor.execute(amount_buy_short_q)
                        amount_buy_short = cursor.fetchone()[0]

                        price_buy_short_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_filled IS NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_buy_short_q)
                        price_buy_short = cursor.fetchone()[0]
                    
                    sold = round(amount_sell_short,8)
                    if buy_count_short > 0:
                        bought = round(amount_buy_short,8)
                    else:
                        bought = 0

                    if grow_f == "1": 
                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_short"], ")")
                        print(LANGUAGES[lang]["statistics_sold_short"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_bought_short"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["test_profit"], "{:.8f}".format(abs((sold-bought)/price_buy_short)), baseCurrency)
                        print("")
                    else:
                        print("-----------------------------")
                        print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_short"], ")")
                        print(LANGUAGES[lang]["statistics_sold_short"], str(sold), quoteCurrency)
                        print(LANGUAGES[lang]["statistics_bought_short"], str(bought), quoteCurrency)
                        print(LANGUAGES[lang]["test_profit"], "{:.8f}".format(abs(sold-bought)), quoteCurrency )
                        print("")                        

                else:
                    not_bought_yet = row[0]
                    amount_sell_short_q = """
                      SELECT
                          SUM(order_spent)
                      FROM
                          orders
                      WHERE
                          order_market='%s'
                          AND order_type = 'sell'
                          AND algorithm = 'short'
                          AND order_filled IS NOT NULL
                          AND order_cancelled IS NULL
                    """ % market
                    cursor.execute(amount_sell_short_q)

                    amount_sell_short = cursor.fetchone()[0]
                    if buy_count_short > 0:
                        amount_buy_short_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_cancelled IS NULL
                              AND order_filled IS NOT NULL
                        """ % market
                        cursor.execute(amount_buy_short_q)
                        amount_buy_short = cursor.fetchone()[0]
                        
                        price_buy_short_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_filled IS NOT NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_buy_short_q)
                        price_buy_short = cursor.fetchone()[0]
                    else:
                        amount_buy_short_q = """
                          SELECT
                              SUM(order_spent)
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_cancelled IS NULL
                              AND order_filled IS NULL
                        """ % market
                        cursor.execute(amount_buy_short_q)
                        amount_buy_short = cursor.fetchone()[0]
                        
                        price_buy_short_q = """
                          SELECT
                              order_price
                          FROM
                              orders
                          WHERE
                              order_market='%s'
                              AND order_type = 'buy'
                              AND algorithm = 'short'
                              AND order_filled IS NULL
                          ORDER BY order_created DESC
                        """ % (market)
                        cursor.execute(price_buy_short_q)
                        price_buy_short = cursor.fetchone()[0]

                    if amount_sell_short != None:
                        sold = round(amount_sell_short,8)
                        if buy_count_short > 0:
                            bought = round(amount_buy_short,8)
                        else:
                            bought = 0

                        if grow_f == "1":
                            print("-----------------------------")
                            print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_short"] + ")")
                            print(LANGUAGES[lang]["statistics_sold_short"], str(sold), quoteCurrency)
                            print(LANGUAGES[lang]["statistics_bought_short"], str(bought), quoteCurrency)
                            print(LANGUAGES[lang]["statistics_if_will_buy_short"], "{:.8f}".format(abs((sold-bought-not_bought_yet)/price_buy_short)), baseCurrency)
                            print("")
                        else:
                            print("-----------------------------")
                            print(LANGUAGES[lang]["market_label"], market[0], " (", LANGUAGES[lang]["statistics_short"] + ")")
                            print(LANGUAGES[lang]["statistics_sold_short"], str(sold), quoteCurrency)
                            print(LANGUAGES[lang]["statistics_bought_short"], str(bought), quoteCurrency)
                            print(LANGUAGES[lang]["statistics_if_will_buy_short"], "{:.8f}".format(abs(sold-bought-not_bought_yet)), quoteCurrency)
                            print("")
                            
            if buy_count_long == 0 and sell_count_short == 0:
                print("-----------------------------")
                print(LANGUAGES[lang]["market_label"], market[0])
                print(LANGUAGES[lang]["statistics_are_not_available"])
                print("")
