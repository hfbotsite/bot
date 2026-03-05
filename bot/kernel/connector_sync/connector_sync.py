import ccxt
import time
import sqlite3
import logging
import time
from datetime import datetime
#from ccxt.base.decimal_to_precision import (ROUND_DOWN, ROUND_UP, TICK_SIZE, TRUNCATE, decimal_to_precision)

logging.basicConfig(filename="logs/output.log", level=logging.INFO)

class Connector_sync():
	def __init__(self):
		self.exchange = None

	def configure(self, config):
		exchange_id = config.get("bot", "exchange")
		exchange_class = getattr(ccxt, exchange_id)

		if exchange_id == "kucoinfutures":
			self.exchange = exchange_class({
				"apiKey": config.get(exchange_id, "api_key"),
				"secret": config.get(exchange_id, "api_secret"),
				"password": config.get(exchange_id, "password"),
				"timeout": 30000,
				"enableRateLimit": True,
				"options": {'defaultType': 'future'}
			})
		# elif exchange_id == "ftx":
		# 	self.exchange = exchange_class({
		# 		"apiKey": config.get(exchange_id, "api_key"),
		# 		"secret": config.get(exchange_id, "api_secret"),
		# 		"headers": {'FTX-SUBACCOUNT': config.get(exchange_id, "subaccount")},
		# 		"timeout": 30000,
		# 		"enableRateLimit": True,
		# 		"options": {'defaultType': 'future'}
		# 	})
		else:
			self.exchange = exchange_class({
				"apiKey": config.get(exchange_id, "api_key"),
				"secret": config.get(exchange_id, "api_secret"),
				"timeout": 30000,
				"enableRateLimit": True,
				"options": {'defaultType': 'future', "adjustForTimeDifference": True}
			})
		self.exchange.load_markets()
		return exchange_id



	def change_leverage(self, symbol, leverage):
		# if isinstance(self.exchange, ccxt.ftx):
		# 	q = self.exchange.private_post_account_leverage({"leverage": leverage, })
		# if isinstance(self.exchange, ccxt.kucoinfutures):
		# 	#q = 0
		# 	q = self.exchange.private_post_account_leverage({"symbol": symbol, "leverage": leverage, })
		# else:
		q = self.exchange.fapiPrivate_post_leverage({"symbol": symbol, "leverage": leverage, })
		return q



	def get_ohlcv(self, market, interval):
		return self.exchange.fetch_ohlcv(market, interval, limit=400)

	# Post a market order
	def post_market_order(self, symbol, side, amount, lev):
		params = {'leverage': lev}
		#print(params)
		# return if order size is 0
		if amount == 0:
			return False
		if isinstance(self.exchange, ccxt.kucoinfutures):
			return self.exchange.createOrder(symbol, 'market', side, amount, amount, params=params)
		else:
			return self.exchange.create_order(symbol, 'market', side, amount)

	# Post a market order
	def post_limit_order(self, symbol, side, amount, price):
		# return if order size is 0
		if amount == 0:
			return False
		return self.exchange.create_limit_order(symbol=symbol, side=side, amount=amount, price=price)#, timeInForce=TIME_IN_FORCE_GTC

	# Post a stop order
	def post_stop(self, symbol, side, amount, price):
		# return if order size is 0
		if amount == 0:
			return False
		# if isinstance(self.exchange, ccxt.ftx):
		# 	q = self.exchange.create_order(symbol=symbol, type='stop', side=side, amount=amount, params={"stopPrice": price})
		# else:
		q = self.exchange.create_order(symbol=symbol, type='STOP_MARKET', side=side, amount=amount, params={"stopPrice": price})
		return q

	# Cancel an order
	def cancel_order(self, order_id, symbol):


		#order_type = order_id['info']['type']
		# if isinstance(self.exchange, ccxt.ftx):
		#
		# 	return self.exchange.cancel_order(str(order_id), symbol, params={'method':'privateDeleteConditionalOrdersOrderId'})
		# 	# else:
		# 	# 	return self.exchange.cancel_order(order_id["info"]["orderId"], symbol,
		# 	# 									  {'method': 'privateDeleteOrdersOrderId'})
		# else:
			if type(order_id) is str:
				order_id = self.get_order(order_id, symbol)
			return self.exchange.cancel_order(order_id["info"]["orderId"], symbol)

	# Return bid market price of an asset
	def get_order_book(self, symbol):
		self.exchange.load_markets()
		q = self.exchange.fetch_order_book(symbol)
		time.sleep(0.1)
		#print(q)

		bid_price = q["bids"][0][0]
		ask_price = q["asks"][0][0]

		return float(bid_price), float(ask_price)


	# Return available balance of an asset
	def get_free_balance(self, token):
		self.exchange.load_markets()
		balances = self.exchange.fetch_balance()
		balance = balances.get(token, {})
		free = balance.get('free', 0)
		return free

	# Return available balance of an asset
	def get_balance(self, b_pair, q_pair):
		self.exchange.load_markets()
		q = self.exchange.fetch_balance()
		time.sleep(0.1)
		#print(q)

		# if isinstance(self.exchange, ccxt.ftx):
		# 	for dic in q['info']['result']:
		# 		if dic['coin'] == "USD":
		# 			balance = float(dic['total'])
		# 	#print(balance)
		# 	qq = self.exchange.fetch_positions()
		# 	time.sleep(0.1)
		# 	#print(qq)
		# 	pnl = 0
		# 	entry_pos = 0
		# 	for i in qq:
		# 		if i['info']['future'] == b_pair + "-" + q_pair:
		# 			if i['info']['entryPrice'] != None:
		# 				pnl = float((i['info']['recentPnl']))
		# 				entry_pos = float((i['info']['entryPrice']))
		pnl = 0
		entry_pos = 0
		if isinstance(self.exchange, ccxt.kucoinfutures):
			balance = float(q['info']['data']['marginBalance'])
			qq = self.exchange.fetch_positions()
			#print(qq)
			time.sleep(0.1)
			for i in qq:
				if qq != None:
					entry_pos = float((i['info']['avgEntryPrice']))
					pnl = float((i['info']['unrealisedPnl']))
					realLeverage = float((i['info']['realLeverage']))
					order_id = i['info']['id']
					order_amount = i['info']['currentQty']
					order_price = float(i['info']['markPrice'])
					pnl_pcnt = float(i['info']['unrealisedRoePcnt'])
		else:
			free = q.get(q_pair, {})
			balance = float(free.get('total', 0))

			for dic in q['info']['assets']:
				if dic['asset'] == q_pair:
					pnl = float(dic['unrealizedProfit'])

			entry_pos = q['info']['positions']
			entry_pos = [p for p in entry_pos if p['symbol'] == b_pair+q_pair][0]
			entry_pos = float(entry_pos['entryPrice'])

		if entry_pos == 0:
			return balance
		else:
			return balance, pnl, entry_pos, realLeverage, order_id, order_amount, order_price, pnl_pcnt

	def get_stop_orders(self, symbol):
		q = self.exchange.fetch_open_orders(symbol, params={'method':'privateGetConditionalOrders'})
		#q = self.exchange.fetch_open_orders(symbol)
		#print('open', q)
		if q != []:
			if isinstance(self.exchange, ccxt.kucoinfutures):
				order_id = q[-1]['info']['orderId']
			else:
				order_id = q[-1]['info']['id']
			order_amount = q[-1]['info']['size']
			order_price = q[-1]['info']['price']
		else:
			order_id = 0
			order_amount = 0
			order_price = 0
		return order_id, order_amount, order_price

	# Get all orders
	def get_all_orders(self, symbol):
		q = self.exchange.fetch_orders(symbol, limit=10)
		time.sleep(0.3)
		#print(q)
		order_id = q[-1]['id']
		order_amount = q[-1]['amount']
		order_price = q[-1]['price']
		return order_id, order_amount, order_price

	# Get an order
	def get_order(self, order_id, symbol):
		# if isinstance(self.exchange, ccxt.ftx):
		# 	return self.exchange.fetch_order(order_id, symbol, {'method': 'privateGetOrdersOrderId'})
		# else:
			return self.exchange.fetch_order(order_id, symbol)

	# Return the status of an order
	def get_order_status(self, order_id, symbol):
		# if isinstance(self.exchange, ccxt.ftx):
		# 	q = self.exchange.fetch_open_orders(symbol, params={'method': 'privateGetConditionalOrders'})
		# 	time.sleep(0.1)
		# 	if q:
		# 		if q[-1]['info']["status"] == "open":
		# 			return "open"
		# 		if q[-1]['info']["status"] == "closed":
		# 			return "canceled"
		# 	else:
		# 		return "canceled"
		# else:
			order = self.get_order(order_id, symbol)
			time.sleep(0.1)
			#print('status:', order)
			if order["info"]["status"] == "FILLED":
				return "filled"
			elif order["info"]["status"] == "NEW":
				return "open"
			elif order["info"]["status"] == "CANCELED":
				return "canceled"

	def get_pnl_and_fee(self, symbol, order_id):
		tuple_pnl = []
		tuple_fee = []
		try:
			q = self.exchange.fetch_my_trades(symbol, limit=20)
			time.sleep(0.35)
		except:
			logging.error('%s: %s: %s %s' % (datetime.now(), 'ERROR 9.1', type(e).__name__, str(e)))

		#print('trades:', q)
		try:
			qq = self.exchange.fetch_positions()
			time.sleep(0.35)
		except:
			logging.error('%s: %s: %s %s' % (datetime.now(), 'ERROR 9.2', type(e).__name__, str(e)))
		#print('trades qq:', qq)

		# if isinstance(self.exchange, ccxt.ftx):
		# 	#b_pair = symbol.split('-')[0]
		# 	#q_pair = symbol.split('-')[1]
		# 	for x in qq:
		# 		if x['info']['future'] == symbol:
		# 			tuple_pnl.append(float(x['info']["realizedPnl"]))
		# 	for y in q:
		# 		if y['info']['orderId'] == order_id:
		# 			tuple_fee.append(float(y['info']['fee']))
		# else:
		if isinstance(self.exchange, ccxt.kucoinfutures):
			for x in qq:
				if x['info']['id'] == order_id:
					tuple_pnl.append(float(x['info']["unrealisedPnl"]))
					tuple_fee.append(float(x['info']["posComm"]))
		else:
			for x in q:
				if x['info']['orderId'] == order_id:
					tuple_pnl.append(float(x['info']["realisedPnl"]))
					tuple_fee.append(float(x['info']["commission"]))

		#print('tuple_fee', tuple_fee)
		if len(tuple_pnl) == 0 and len(tuple_fee) == 0:
			return 0, 0
		else:
			return sum(tuple_pnl), sum(tuple_fee)

	# Return klines as a dataframe of an asset
	def get_klines(self, symbol, interval, limit=100):
		klines = self.exchange.fetch_ohlcv(symbol, interval, limit=limit)
		dataframe = pd.DataFrame(klines)
		dataframe.rename(columns={0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 4: 'close'}, inplace=True)
		dataframe.pop(5)
		dataframe.drop(index=dataframe.index[-1], axis=0, inplace=True)
		return dataframe

	# Get market information
	def get_market(self, symbol):
		q = self.exchange.market(symbol)
		#print('Q_m=', q)
		return q

	# Get market precision
	def get_precision(self, symbol):
		market = self.get_market(symbol)
		#print(market)
		return market["precision"]["amount"], market["limits"]["amount"]["min"]

	# Calculate the size of a buy position
	def get_buy_size(self, symbol, amount, price=None, free_currency_balance=None):

		coin = symbol.split("/")[1]

		# get free balance
		if free_currency_balance is None:
			free_currency_balance = self.get_free_balance(coin)

		# apply percentage
		amount = (amount * float(free_currency_balance)) / 100

		# get precision & limit (minimum amount)
		precision, limit = self.get_precision(symbol)

		digits = int(math.sqrt((int(math.log10(precision)) + 1) ** 2)) + 1

		# get price
		if price is None:
			price = self.get_ask(symbol)

		amount /= price

		# apply precision
		amount = self.truncate(amount, digits)

		# apply limit
		if amount < limit:
			return 0

		return amount

	# Calculate the size of a sell position
	def get_sell_size(self, symbol, amount, free_token_balance=None):

		market = symbol.split("/")[0]

		# get free balance
		if free_token_balance is None:
			free_token_balance = self.get_free_balance(market)

		# apply percentage
		amount = (amount * float(free_token_balance)) / 100

		# get precision & limit (minimum amount)
		precision, limit = self.get_precision(market)

		digits = int(math.sqrt((int(math.log10(precision)) + 1) ** 2)) + 1

		# apply precision
		amount = self.truncate(amount, digits)

		# apply limit
		if amount < limit:
			return 0

		return amount



	# Used to set precision of a number
	def truncate(self, number, decimals=0):
		"""
        Returns a value truncated to a specific number of decimal places.
        """
		if not isinstance(decimals, int):
			raise TypeError("decimal places must be an integer.")
		elif decimals < 0:
			raise ValueError("decimal places has to be 0 or more.")
		elif decimals == 0:
			return math.trunc(number)

		factor = 10.0 ** decimals
		return math.trunc(number * factor) / factor