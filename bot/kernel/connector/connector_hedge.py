import asyncio
import ccxt.async_support as ccxt
from ccxt.base.errors import ExchangeNotAvailable
from ccxt.base.decimal_to_precision import (ROUND_DOWN, ROUND_UP, TICK_SIZE, TRUNCATE, decimal_to_precision)
import pandas as pd
import re
import time
import sqlite3
import datetime

type = 'swap'
subType = 'linear'


def get_time():
    now = datetime.datetime.utcnow()
    t = now.isoformat("T", "milliseconds")
    return t + "Z"

class Connector():
	def __init__(self):
		self.exchange = None

	async def configure(self, config, market):
		exchange_id = config.get_value("bot", "exchange")

		exchange_class = getattr(ccxt, exchange_id)

		if exchange_id == "okx":
			self.exchange = exchange_class({
				"apiKey": config.get_value(exchange_id, "api_key"),
				"secret": config.get_value(exchange_id, "api_secret"),
				"password": config.get_value(exchange_id, "password"),
				'options': {'defaultType': 'swap'},
				'headers': {'x-simulated-trading': '0'}
			})
		if exchange_id == "kucoin" or exchange_id == "kucoinfutures":
			self.exchange = exchange_class({
				"apiKey": config.get_value(exchange_id, "api_key"),
				"secret": config.get_value(exchange_id, "api_secret"),
				"password": config.get_value(exchange_id, "password"),
				"timeout": 30000,
				"enableRateLimit": True,
				"options": {'defaultType': 'future'}
			})
		if exchange_id == "bybit":
			self.exchange = exchange_class({
				"apiKey": config.get_value(exchange_id, "api_key"),
				"secret": config.get_value(exchange_id, "api_secret"),
				"timeout": 30000,
				"enableRateLimit": True,
				'defaultType':'swap',
				#"options": {"adjustForTimeDifference": True}
			})

		if exchange_id == "binance":
			self.exchange = exchange_class({
				"apiKey": config.get_value(exchange_id, "api_key"),
				"secret": config.get_value(exchange_id, "api_secret"),
				"timeout": 30000,
				"enableRateLimit": True,
				"options": {'defaultType': 'future', "adjustForTimeDifference": True}
			})

		if exchange_id == "bingx":
			self.exchange = exchange_class({
				"apiKey": config.get_value(exchange_id, "api_key"),
				"secret": config.get_value(exchange_id, "api_secret"),
				"timeout": 30000,
				'enableRateLimit': True,
				'options': {'defaultType': 'swap', 'adjustForTimeDifference': True}
			})

		if exchange_id == "binance":
			mrk = market
		else:
			mrk = market + ':' + market.split('/')[1]
		# if exchange_id != "kucoinfutures":
		# 	try:
		# 		await self.exchange.set_position_mode(hedged=False, symbol=mrk)
		# 		await self.exchange.close()
		# 	except Exception as e:
		# 		print('ERRR', e)
		# 		ff = True
		await self.exchange.load_markets()
		await self.exchange.close()
		return self.exchange

		# await self.exchange.load_markets()
		# await self.exchange.close()
		# return exchange_id

	async def get_ask_bid(self, symbol):
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]

		order_book = await self.exchange.fetch_order_book(market, limit=10)
		if isinstance(self.exchange, ccxt.kucoinfutures):
			ask_price = order_book['asks'][-1][0] if len(order_book['asks']) > 0 else None
			bid_price = order_book['bids'][-1][0] if len(order_book['bids']) > 0 else None
		else:
			ask_price = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
			bid_price = order_book['bids'][0][0] if len(order_book['bids']) > 0 else None

		await self.exchange.close()
		return ask_price, bid_price

	async def set_margin_mode(self, symbol, margin_mode, position_mode, leverage):
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]
		try:
			await self.exchange.set_margin_mode(margin_mode, market, {'leverage': leverage})
		except Exception as e:
			print('SET MARGIN MODE ERROR', str(e))
		try:
			if position_mode == 'hedge':
				q = await self.exchange.set_position_mode(hedged=True, symbol=market, params={})
			else:
				await self.exchange.set_position_mode(hedged=False, symbol=market, params={})
		except Exception as e:
			print('SET POSITION MODE ERROR', str(e))
		await self.exchange.close()

	async def change_leverage(self, symbol, side, position_mode, leverage):
		# if isinstance(self.exchange, ccxt.ftx):
		# 	q = self.exchange.private_post_account_leverage({"leverage": leverage, })
		# if isinstance(self.exchange, ccxt.kucoinfutures):
		# 	#q = 0
		# 	q = self.exchange.private_post_account_leverage({"symbol": symbol, "leverage": leverage, })
		# else:
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		elif isinstance(self.exchange, ccxt.bybit) or isinstance(self.exchange, ccxt.okx):
			market = symbol.split('/')[0]+symbol.split('/')[1]
			if isinstance(self.exchange, ccxt.okx):
				leverage = int(leverage)
		elif isinstance(self.exchange, ccxt.bingx):
			market = symbol.split('/')[0] + '-' + symbol.split('/')[1]
			leverage = int(leverage)
		else:
			market = symbol + ':' + symbol.split('/')[1]
		# if isinstance(self.exchange, ccxt.binance):
		try:
			if isinstance(self.exchange, ccxt.bingx):
				if position_mode == 'hedge':
					if side == 'buy':
						pos_side = 'LONG'
					else:
						pos_side = 'SHORT'
					q = await self.exchange.set_leverage(leverage, market, {'side': pos_side})
				else:
					q = await self.exchange.set_leverage(leverage, market, {'side': 'BOTH'})
			else:
				q = await self.exchange.set_leverage(leverage, market)
		except Exception as e:
			print('%s: %s %s' % ('CHANGE LEVERAGE ERROR', type(e).__name__, str(e)))
		await self.exchange.close()

		return q

	# Post a market order
	async def post_market_order(self, symbol, side, amount, leverage, reason, position_mode):
		# return if order size is 0
		if amount == 0:
			return False

		if reason == 'sell_button':
			params = {'leverage': leverage, 'reduceOnly': True}
		else:
			if position_mode == 'hedge':
				if side == 'buy':
					pos_side = 1
				else:
					pos_side = 2
				params = {'leverage': leverage, 'positionIdx': pos_side}
			else:
				params = {'leverage': leverage}



		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			conn = sqlite3.connect('bot.db', check_same_thread=False)
			cursor = conn.cursor()
			cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % symbol)
			precisions = cursor.fetchall()[0]
			amountPrecision, pricePrecision, amountLimit = precisions
			am = int(amount/amountLimit)
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(symbol=market, type='market', side=side, amount=am, price=None, params=params)
			await self.exchange.close()
		elif isinstance(self.exchange, ccxt.bybit):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(symbol=market, type='market', side=side, amount=amount, price=None, params=params)
			await asyncio.sleep(1)
			await self.exchange.close()
		elif isinstance(self.exchange, ccxt.bingx):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(market, 'market', side, amount, None, {'positionSide': 'BOTH'})
		else:
			q = await self.exchange.create_order(symbol=symbol, type='market', side=side, amount=amount, price=None, params={})
			await self.exchange.close()
		return q

	# Post a limit order
	async def post_limit_order(self, symbol, side, amount, price, leverage):
		# return if order size is 0
		if amount == 0:
			return False

		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			conn = sqlite3.connect('bot.db', check_same_thread=False)
			cursor = conn.cursor()
			cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % symbol)
			precisions = cursor.fetchall()[0]

			amountPrecision, pricePrecision, amountLimit = precisions
			am = int(amount/amountLimit)
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(symbol=market, type='limit', side=side, amount=am, price=price, params={'leverage': leverage})
		elif isinstance(self.exchange, ccxt.bybit):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(symbol=market, type='limit', side=side, amount=amount, price=price, params={'leverage': leverage})
		elif isinstance(self.exchange, ccxt.bingx):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(market, 'limit', side, amount, price, {'positionSide': 'BOTH'})
		else:
			q = await self.exchange.create_order(symbol=symbol, type='limit', side=side, amount=amount, price=price, params={})

		await self.exchange.close()
		return  q

	# Post a stop-loss order
	async def post_stop_loss_order(self, symbol, side, amount, trigger_price, leverage):
		if amount == 0:
			return False

		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			conn = sqlite3.connect('bot.db', check_same_thread=False)
			cursor = conn.cursor()
			cursor.execute("""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % symbol)
			precisions = cursor.fetchall()[0]
			amountPrecision, pricePrecision, amountLimit = precisions
			am = int(amount/amountLimit)
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(symbol=market, type='market', side=side, amount=am, price=trigger_price, params={'stopPrice': trigger_price})
		elif isinstance(self.exchange, ccxt.bybit):
			market = symbol + ':' + symbol.split('/')[1]
			if side == 'sell':
				trigger_dir = 'below'
			else:
				trigger_dir = 'above'
			q = await self.exchange.create_order(symbol=market, type='market', side=side, amount=amount, price=trigger_price, params={'triggerPrice': trigger_price, 'triggerDirection': trigger_dir, 'leverage': leverage})
		elif isinstance(self.exchange, ccxt.bingx):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.create_order(market, 'market', side, amount, None, {'stopLossPrice': trigger_price, 'positionSide': 'BOTH'})
		else:
			q = await self.exchange.create_order(symbol=symbol, type='STOP_MARKET', side=side, amount=amount, params={'stopPrice': trigger_price})
		await self.exchange.close()

		return q

	async def get_open_orders(self, symbol, limit):
		if isinstance(self.exchange, ccxt.bybit):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]
		q_open = await self.exchange.fetch_open_orders(market, limit)
		await asyncio.sleep(0.1)
		await self.exchange.close()
		return q_open

	async def get_trades(self, symbol, limit):
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]
		now = ccxt.bybit.milliseconds()
		week = 604800000
		since = now - week
		q = await self.exchange.fetch_trades(market, since, limit)
		return q

	# Get all orders
	async def get_all_orders(self, symbol, type):
		#p = []
		#print(int(time.time()))
		q = None
		if isinstance(self.exchange, ccxt.binance):
			q = await self.exchange.fetch_orders(symbol)
		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			market = symbol + ':' + symbol.split('/')[1]
			if isinstance(self.exchange, ccxt.okx) and type == 'stop_loss':
				closed_par = {'trigger': True}
				open_par = {'stop': True, 'ordType': 'trigger'}
			else:
				closed_par = {}
				open_par = {}

			q_closed = await self.exchange.fetch_closed_orders(symbol=market, params=closed_par)
			await asyncio.sleep(0.2)

			q_open = await self.exchange.fetch_open_orders(symbol=market, params=open_par)
			await asyncio.sleep(0.2)

			q = q_open + q_closed
		if isinstance(self.exchange, ccxt.bybit):
			market = symbol + ':' + symbol.split('/')[1]
			q_orders = []
			now = ccxt.bybit.milliseconds()
			week = 604800000
			for i in range(0, 4):
				since = now - (i + 1) * week
				until = now - i * week
				item = await self.exchange.fetch_orders(symbol=market, since=since, params={'until': until})
				q_orders.extend(item)

			await self.exchange.close()
			q = q_orders
		if isinstance(self.exchange, ccxt.bingx):
			market = symbol + ':' + symbol.split('/')[1]
			q = await self.exchange.fetch_orders(market)

		return q

	# Get an order
	async def get_order(self, order_id, symbol, type):
		qq = None
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]
		try:
			if isinstance(self.exchange, ccxt.binance) or isinstance(self.exchange, ccxt.bingx) or (isinstance(self.exchange, ccxt.okx) and type=='market'):

				qq = await self.exchange.fetch_order(order_id, market)
				#print(qq)
				#await asyncio.sleep(0.5)

			else:
				q = await self.get_all_orders(symbol, type)
				#print(q)
				for item in q:
					if item['id'] == order_id:
						qq = item


		except Exception as e:
			print(symbol, '%s: %s %s' % ('FETCH ORDER ERROR 01', type(e).__name__, str(e)))
		finally:
			await self.exchange.close()

		if isinstance(self.exchange, ccxt.binance) or isinstance(self.exchange, ccxt.bybit) or isinstance(self.exchange, ccxt.bingx) or isinstance(self.exchange, ccxt.okx):
			if qq['type'] == 'market' and (not qq['stopPrice'] or not qq['triggerPrice']):
				price = float(qq['average'])
			elif (qq['stopPrice'] or qq['triggerPrice']):
				price = float(qq['triggerPrice'])
			else:
				price = float(qq['price'])
		else:
			price = float(qq['price'])

		if isinstance(self.exchange, ccxt.binance):
			if qq['status'] == 'closed' and qq['type'] == 'limit':
				fee = float(qq['cost'] * 0.02 / 100)
			elif qq['status'] == 'closed' and qq['type'] == 'market':
				fee = float(qq['cost'] * 0.04 / 100)
			else:
				fee = 0
		elif isinstance(self.exchange, ccxt.okx):
			fee = 0
		else:
			fee = qq['fee']['cost']

		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			conn = sqlite3.connect('bot.db', check_same_thread=False)
			cursor = conn.cursor()
			cursor.execute(
				"""SELECT amount_precision, price_precision, amount_limit FROM limits WHERE market='%s'""" % symbol)
			precisions = cursor.fetchall()[0]
			amountPrecision, pricePrecision, amountLimit = precisions
			am = float(qq['amount'] * amountLimit)
			if isinstance(self.exchange, ccxt.okx) and qq['type'] == 'trigger':
				re = am
			else:
				re = float(qq['remaining'] * amountLimit)
		else:
			am = qq['amount']
			re = qq['remaining']

		p = {'id': qq['id'], 'status': qq['status'], 'side': qq['side'], 'price': price, 'amount': am,
			 'cost': qq['cost'], 'remaining': re, 'fee': fee}
		#print(p)
		return p

	# Cancel an order
	async def cancel_order(self, order_id, symbol):
		if isinstance(self.exchange, ccxt.binance):
			s = symbol
		else:
			s = symbol + ':' + symbol.split('/')[1]
		q = None
		try:
			q = await self.exchange.cancel_order(str(order_id), s)
		except Exception as e:
			print(symbol, '%s: %s %s' % ('CANCEL ORDER ERROR 01', type(e).__name__, str(e)))
		await self.exchange.close()
		return q

	# Return bid market price of an asset
	async def get_order_book(self, symbol, limit):
		q = await self.exchange.fetch_order_book(symbol)
		await self.exchange.close()
		bids = q['bids']
		asks = q['asks']
		return bids[:limit], asks[:limit]

	# Return available balance of an asset
	def get_free_balance(self, token):
		self.exchange.load_markets()
		balances = self.exchange.fetch_balance()
		balance = balances.get(token, {})
		free = balance.get('free', 0)
		return free


	# Get trades
	async def get_my_trades(self, symbol):
		if isinstance(self.exchange, ccxt.binance):
			market = symbol
		else:
			market = symbol + ':' + symbol.split('/')[1]
		try:
			q = await self.exchange.fetch_my_trades(symbol=market, limit=1)
		except Exception as e:
			print(symbol, '%s: %s' % ('GET MY trades ERROR', str(e)))
		await self.exchange.close()
		return q if q else []

	# Return available balance of an asset
	async def get_balance(self, b_pair, q_pair, config, position_mode):
		MARKETS = []
		BASE_COIN = config.get_value("bot", "base_coin")
		QUOTE_COIN = config.get_value("bot", "quote_coin")
		base_coins = BASE_COIN.replace(' ', '').split(',')
		for i in base_coins:
			MARKETS.append(str(i) + "/" + str(QUOTE_COIN))
		N = len(MARKETS)

		pos_average = 0
		#type, ['swap', 'option', 'spot']
		#subType, ['linear', 'inverse']
		if isinstance(self.exchange, ccxt.okx):
			q = await self.exchange.fetch_balance()
			balance = q[q_pair].get('total', 0)
			free = q[q_pair].get('free', 0)
			qq = await self.exchange.fetch_positions([b_pair + '/' + q_pair + ':' + q_pair])
			await self.exchange.close()
			if qq:
				if qq[0]['entryPrice'] != None:
					pnl = float(qq[0]['unrealizedPnl'])
					pos_average = float(qq[0]['entryPrice'])
					leverage = float(qq[0]['leverage'])
					side = qq[0]['side']
					pos_contracts = float(qq[0]['contracts'])
					pos_contract_size = float(qq[0]['contractSize'])
					pos_amount = float(pos_contracts * pos_contract_size)
					if side == 'short':
						pos_amount = pos_amount * - 1
					pos_cost = abs(float(qq[0]['collateral']))
					pos_id = qq[0]['id']
					if qq[0]['liquidationPrice'] != None:
						liquidation = float(qq[0]['liquidationPrice'])
					else:
						initial_margin = float(pos_cost) / leverage
						total_equity = float(balance) - N * initial_margin
						if side == 'long':
							liquidation = round(pos_average * (1 - (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
						else:
							liquidation = round(pos_average * (1 + (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)

					roe_pcnt = float(qq[0]['percentage'])
					return {'balance': balance, 'free': free, 'pnl': pnl, 'pos_average': pos_average, 'leverage': leverage,
							'pos_amount': pos_amount, 'pos_cost': pos_cost, 'order_id': pos_id, 'roe_pcnt': str(roe_pcnt) + '%',
							'liquidation': liquidation, 'side': side}

			else:
				return {'balance': balance}



		if isinstance(self.exchange, ccxt.kucoinfutures):
			q = await self.exchange.fetch_balance()
			balance = float(q['info']['data']['accountEquity'])
			free = q[q_pair].get('free', 0)

			qq = await self.exchange.fetch_positions([b_pair+'/'+q_pair + ':' + q_pair])
			await self.exchange.close()

			#time.sleep(0.1)
			for i in qq:
				if qq[0]['entryPrice'] != None:
					pnl = float(qq[0]['unrealizedPnl'])
					pos_average = float(qq[0]['entryPrice'])
					leverage = float(config.get_value("bot", "leverage"))
					real_leverage = float(qq[0]['leverage'])
					side = qq[0]['side']
					pos_contracts = float(qq[0]['contracts'])
					pos_contract_size = float(qq[0]['contractSize'])
					pos_amount = float(pos_contracts * pos_contract_size)
					if side == 'short':
						pos_amount = pos_amount * - 1
					pos_cost = float(qq[0]['notional'])
					pos_id = qq[0]['id']
					if qq[0]['liquidationPrice'] != None:
						liquidation = float(qq[0]['liquidationPrice'])
					else:
						initial_margin = float(pos_cost) / leverage
						total_equity = float(balance) - N * initial_margin
						if side == 'long':
							liquidation = round(pos_average * (1 - (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
						else:
							liquidation = round(pos_average * (1 + (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)

				if pos_average > 0:
					roe_pcnt = round(pnl/pos_cost*100*leverage, 2)
					if pnl > 0:
						roe_pcnt = abs(roe_pcnt)
					else:
						roe_pcnt = roe_pcnt * - 1
					return {'balance': balance, 'free': free, 'pnl': pnl, 'pos_average': pos_average, 'leverage': leverage,
							'pos_amount': pos_amount, 'pos_cost': pos_cost, 'order_id': pos_id, 'roe_pcnt': str(roe_pcnt) + '%',
							'liquidation': liquidation, 'side': side}
				else:

					return {'balance': balance}




		if isinstance(self.exchange, ccxt.binance):
			q = await self.exchange.fetch_balance()
			await asyncio.sleep(0.2)
			await self.exchange.close()

			#free = q.get(q_pair, {})
			#balance = float(free.get('total', 0))
			balance = q['info']['totalMarginBalance']
			free = q['info']['availableBalance']

			for dic in q['info']['positions']:
				if dic['symbol'] == b_pair+q_pair:
					pos_average = float(dic['entryPrice'])

			if pos_average > 0:
				qq = await self.exchange.fetch_positions_risk([b_pair+q_pair])
				#print(qq)
				await asyncio.sleep(0.1)
				await self.exchange.close()
				#print(qq)

				#balance = float(q[0]['collateral'])
				pnl = float(qq[0]['unrealizedPnl'])
				pos_average = float(qq[0]['entryPrice'])
				leverage = float(qq[0]['leverage'])
				side = qq[0]['side']
				pos_contracts = float(qq[0]['contracts'])
				pos_contract_size = float(qq[0]['contractSize'])
				pos_amount = float(pos_contracts * pos_contract_size)
				if side == 'short':
					pos_amount = pos_amount * - 1
				pos_cost = float(qq[0]['notional'])
				if qq[0]['liquidationPrice'] != None:
					liquidation = float(qq[0]['liquidationPrice'])
				else:
					initial_margin = float(pos_cost) / leverage
					total_equity = float(balance) - N * initial_margin
					if side == 'long':
						liquidation = round(pos_average * (1 - (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
					else:
						liquidation = round(pos_average * (1 + (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
				pos_id = None


				roe_pcnt = round(pnl / pos_cost * 100 * leverage, 2)
				if pnl > 0:
					roe_pcnt = abs(roe_pcnt)
				else:
					roe_pcnt = abs(roe_pcnt) * - 1

				return {'balance': balance, 'free': free, 'pnl': pnl, 'pos_average': pos_average, 'leverage': leverage,
						'pos_amount': pos_amount, 'pos_cost': pos_cost, 'order_id': pos_id, 'roe_pcnt': str(roe_pcnt) + '%',
						'liquidation': liquidation, 'side': side}
			else:
				return {'balance': balance}


		if isinstance(self.exchange, ccxt.bybit):
			q = await self.exchange.fetch_balance(params={'type': 'swap'})
			await asyncio.sleep(0.1)
			await self.exchange.close()
			balance = 0
			for i, item in enumerate(q['info']['result']['list'][0]['coin']):
				if item['coin'] == q_pair:
					balance = item['equity']

			free = q[q_pair].get('free', 0)
			qq = await self.exchange.fetch_positions(b_pair+'/'+q_pair + ':' + q_pair)

			await asyncio.sleep(0.5)
			await self.exchange.close()

			def process_position(pos):
				collateral = pos['collateral']
				pnl = float(pos['unrealizedPnl'])
				pos_average = float(pos['entryPrice'])
				leverage = float(pos['leverage'])
				side = pos['side']
				pos_amount = float(pos['contracts'])
				pos_contract_size = float(pos['contractSize'])

				if side == 'short':
					pos_amount = pos_amount * -1
				pos_cost = float(pos['notional'])
				if pos['liquidationPrice'] is not None:
					liquidation = float(pos['liquidationPrice'])
				else:
					initial_margin = float(pos_cost) / leverage
					total_equity = float(balance) - N * initial_margin
					if side == 'long':
						liquidation = round(
							pos_average * (1 - (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
					else:
						liquidation = round(
							pos_average * (1 + (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)

				pos_id = None
				roe_pcnt = round((pnl / collateral) * 100, 2)
				if pnl > 0:
					roe_pcnt = abs(roe_pcnt)
				else:
					roe_pcnt = abs(roe_pcnt) * -1

				return {
					'balance': balance,
					'free': free,
					'pnl': pnl,
					'pos_average': pos_average,
					'leverage': leverage,
					'pos_amount': pos_amount,
					'pos_cost': pos_cost,
					'order_id': pos_id,
					'roe_pcnt': str(roe_pcnt) + '%',
					'liquidation': liquidation,
					'side': side
				}

			# Logic for hedge mode

			if len(qq) > 1:
				long_position = None
				short_position = None

				for i, pos in enumerate(qq):
					if qq[i]['entryPrice'] is not None:
						if pos['side'] == 'long':
							long_position = process_position(pos)
						elif pos['side'] == 'short':
							short_position = process_position(pos)

					if long_position and short_position:
						return [long_position, short_position]
					elif long_position:
						return long_position
					elif short_position:
						return short_position
					else:
						return {'balance': balance}
			else:
				# Logic for one_way mode
				if qq[0]['entryPrice'] is not None:
					return process_position(qq[0])
				else:
					return {'balance': balance}


		if isinstance(self.exchange, ccxt.bingx):
			q = await self.exchange.fetch_balance(params={'type': 'swap'})
			await asyncio.sleep(0.1)
			await self.exchange.close()
			balance = 0

			if q['info']['data']['balance']['asset'] == q_pair:
				balance = q['info']['data']['balance']['equity']
			#print('balance=', balance)
			free = q[q_pair].get('free', 0)

			qq = await self.exchange.fetch_positions(symbols=[b_pair+'-'+q_pair])

			await asyncio.sleep(0.5)
			await self.exchange.close()

			if qq:
				for i, item in enumerate(qq):
					pnl = float(item['info']['unrealizedProfit'])
					pos_average = float(item['entryPrice'])
					leverage = float(item['info']['leverage'])
					side = item['side']
					pos_amount = float(item['info']['positionAmt'])

					if side == 'short':
						pos_amount = pos_amount * - 1
					pos_cost = float(item['info']['positionValue'])
					if item['info']['liquidationPrice'] != None:
						liquidation = float(item['info']['liquidationPrice'])
					else:
						initial_margin = float(pos_cost) / leverage
						total_equity = float(balance) - N * initial_margin
						if side == 'long':
							liquidation = round(pos_average * (1 - (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)
						else:
							liquidation = round(pos_average * (1 + (initial_margin + total_equity - pos_cost) / (pos_cost * leverage)), 8)

					pos_id = item['id']

					if pos_average > 0:
						roe_pcnt = round(float(item['info']['pnlRatio'])*100,2)
					else:
						roe_pcnt = 0

					return {'balance': balance, 'free': free, 'pnl': pnl, 'pos_average': pos_average, 'leverage': leverage,
							'pos_amount': pos_amount, 'pos_cost': pos_cost, 'order_id': pos_id, 'roe_pcnt': str(roe_pcnt) + '%',
							'liquidation': liquidation, 'side': side}

			else:
				return {'balance': balance}


	async def get_klines(self, e_, trade_pair, timeframe, limit):
		dict_sec = {'1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '2h': 7200, '4h': 14400, '12h': 43200, '1d': 86400}

		if isinstance(self.exchange, ccxt.binance):
			m = trade_pair
		else:
			m = trade_pair + ':' + trade_pair.split('/')[1]

		try:
			if isinstance(self.exchange, ccxt.kucoinfutures):
				now_min = int(round(time.time(), 0)) // dict_sec[timeframe] * dict_sec[timeframe]
				start_min = now_min - dict_sec[timeframe] * limit
				url = "https://api-futures.kucoin.com" + "/api/v1/kline/query?symbol=" + m + "&granularity=" + str(
					dict_sec[timeframe]) + "&from=" + str(start_min * 1000)
				payload = {}
				files = {}
				headers = {}
				data_df = requests.request("GET", url, headers=headers, data=payload, files=files)
				await asyncio.sleep(1.0)
				data_df = data_df.json()
				ohlcv = data_df['data']
			if isinstance(self.exchange, ccxt.bingx):
				timeframe_in_seconds = dict_sec[timeframe]
				since = int((datetime.now() - timedelta(seconds=timeframe_in_seconds * limit)).timestamp() * 1000)
				ohlcv = await self.exchange.fetch_ohlcv(m, timeframe, since, limit)
			else:
				ohlcv = await self.exchange.fetch_ohlcv(m, timeframe, None, limit)

			df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
			df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
			await self.exchange.close()
			return df, df['close'].iloc[-1], None

		except Exception as e:
			await self.exchange.close()
			# Возвращаем None для content и сообщение об ошибке
			error_message = f"Error in fetch_ohlcv_data: {e}"
			return None, None, error_message

	# Get market information
	def get_market(self, symbol):
		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			market = symbol + ':' + symbol.split('/')[1]
		else:
			market = symbol
		q = self.exchange.market(market)
		#print('Q_m=', q)
		return q

	# Get market precision
	def get_precision(self, market):
		#print('QWER 0')
		def remove_exponent(value):
			a = re.sub('e([-+])?[0]*', r"\1", '%.4g' % value)
			if int(str(value).split('e')[1]) < 0:
				result = int(a.split('-')[1])
			else:
				result = int(int(a.split('-')[0]) * (10 ** int(a.split('-')[1])))
			return result


		if isinstance(self.exchange, ccxt.binance):
			symbol = market
		else:
			symbol = market + ':' + market.split('/')[1]

		pair_settings = {}
		try:
			q = self.exchange.market(symbol)
			#print(q)
		except Exception as e:
			print(f"Произошла ошибка при получении настроек пары {symbol} на бирже {self.exchange}: {e}")

		if isinstance(self.exchange, ccxt.bingx) or isinstance(self.exchange, ccxt.binance):
			ap = int(q['precision']['amount'])
			pp = int(q['precision']['price'])
		else:
			a_pr = q['precision']['amount']
			p_pr = q['precision']['price']

			if 'e' in str(a_pr):
				ap = remove_exponent(a_pr)
			else:
				ap = len(str(a_pr).split('.')[1])
			if 'e' in str(p_pr):
				pp = remove_exponent(p_pr)
			else:
				pp = len(str(p_pr).split('.')[1])

		if isinstance(self.exchange, ccxt.kucoinfutures) or isinstance(self.exchange, ccxt.okx):
			ma = q["contractSize"]

		elif isinstance(self.exchange, ccxt.bingx):
			ma = round(float(q['limits']['amount']['min']), 12)
			if ma == None:
				ma = q['info']['tradeMinQuantity']
		else:
			ma = q["limits"]["amount"]["min"]

		#pair_settings = {'amount_precision': ap, 'price_precision': pp, 'min_amount': ma}


		#await self.exchange.close()
		return ap, pp, ma

	def get_min_limits(self, market):
		q = self.exchange.market(market)
		return q["limits"]["amount"]["min"], q["limits"]["cost"]["min"]