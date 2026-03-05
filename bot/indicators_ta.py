import math
import pandas as pd
import numpy as np

def sma(data, period):
    if len(data) == 0:
        raise Exception("Empty data")
    if period <= 0:
        raise Exception("Invalid period")

    interm = 0
    result = []
    nan_inp = 0

    for i, v in enumerate(data):
        if math.isnan(data[i]):
            result.append(math.nan)
            interm = 0
            nan_inp += 1
        else:
            interm += v
            if (i+1 - nan_inp) < period:
                result.append(math.nan)
            else:
                result.append(interm/float(period))
                if not math.isnan(data[i+1-period]):
                    interm -= data[i+1-period]
    return result

def generalEMA(data, period, multiplier):
    if period <= 1:
        raise Exception("Invalid period")

    _sma = sma(data, period)

    result = []
    for k, v in enumerate(_sma):
        if math.isnan(v):
            result.append(math.nan)
        else:
            prev = result[k-1]
            if math.isnan(prev):
                result.append(v)
                continue
            ema = (data[k]-prev)*multiplier + prev
            result.append(ema)
    return result

# def EMA(data, period):
#     return generalEMA(data, period, 2/(float(period)+1.0))

def MA(s, n):
    return pd.Series(s).rolling(n).mean().values

def ema(data, period):
    return generalEMA(data, period, 2/(float(period)+1.0))

def EMA(S, N):               # alpha=2/(span+1)
    return pd.Series(S).ewm(span=N, adjust=False).mean().values

def SMA(S, N, M=1):        #   alpha=1/(1+com)
    return pd.Series(S).ewm(com=N-M, adjust=True).mean().values

# Synonym to EMA
def EWMA(data, period):
    return EMA(data, period)

# Modified moving average
def SMMA(data, period):
    return generalEMA(data, period, 1/(float(period)))

# Synonym to SMMA
def RMA(data, period):
    return SMMA(data, period)
# Synonym to SMMA
def MMA(data, period):
    return SMMA(data, period)

# Double exponential moving average
def D2(data, period):
    ema = EMA(data, period)
    ema_ema = EMA(ema, period)
    e2 = list(map(lambda x: x*2, ema))
    
    result = []
    
    for i in range(len(data)):
        result.append(e2[i] - ema_ema[i])
    return result

# Double exponential moving average
def DEMA(data, period):
    return D2(data, period)

# Double exponential moving average
def DMA(data, period):
    return D2(data, period)

# Triple Exponential Moving Average
def T3(data, period):
    e1 = EMA(data, period)
    e2 = EMA(e1, period)
    e3 = EMA(e2, period)

    e1 = list(map(lambda x: x*3, e1))
    e2 = list(map(lambda x: x*3, e2))

    result = []
    for i in range(len(data)):
        result.append(e1[i] - e2[i] + e3[i])
        
    return result

# Triple Exponential Moving Average
def TEMA(data, period):
    return T3(data, period)

# Triple Exponential Moving Average
def TMA(data, period):
    return T3(data, period)

# Moving average convergence/divergence
def MACD(data, fastperiod, slowperiod, signalperiod):
    macd, macdsignal, macdhist = [], [], []

    fast_ema = ema(data, fastperiod)
    slow_ema = ema(data, slowperiod)
    
    diff = []

    for k, fast in enumerate(fast_ema):
        if math.isnan(fast) or math.isnan(slow_ema[k]):
            macd.append(math.nan)
            macdsignal.append(math.nan)
        else:
            macd.append(fast-slow_ema[k])
            diff.append(macd[k])

    diff_ema = ema(diff, signalperiod)
    macdsignal = macdsignal + diff_ema

    for k, ms in enumerate(macdsignal):
        if math.isnan(ms) or math.isnan(macd[k]):
            macdhist.append(math.nan)
        else:
            macdhist.append(macd[k] - macdsignal[k])

    return macd, macdsignal, macdhist

def AROON(data, n):
    df = data.copy()
    aroon_up = df['high'].rolling(n+1).apply(lambda x: x.argmax(), raw=True) / n * 100
    aroon_down = df['low'].rolling(n+1).apply(lambda x: x.argmin(), raw=True) / n * 100
    return aroon_up.values[-1], aroon_down.values[-1]

# Relative strength index
def RSI(data, period):
    u_days = []
    d_days = []

    for i, _ in enumerate(data):
        if i == 0:
            u_days.append(0)
            d_days.append(0)
        else:
            if data[i] > data[i-1] :
                u_days.append(data[i] - data[i-1])
                d_days.append(0)
            elif data[i] < data[i-1]:
                d_days.append(data[i-1] - data[i])
                u_days.append(0)
            else:
                u_days.append(0)
                d_days.append(0)

    smma_u = SMMA(u_days, period)
    smma_d = SMMA(d_days, period)

    result = []

    for k, _ in enumerate(data):
        if smma_d[k] == 0:
            result.append(100)
        else:
            result.append(100 - (100 / (1 + smma_u[k]/smma_d[k])))

    return result

# Stochastic oscillator
def STOCH(data, period, k, d):
    df = data.copy()
    l = df['low'].rolling(window=period).min()
    h = df['high'].rolling(window=period).max()
    df['k_fast'] = 100 * (df['close'] - l) / (h - l)
    df['d_fast'] = MA(df['k_fast'], k)

    df['k_slow'] = df["d_fast"]
    df['d_slow'] = MA(df['k_slow'], d)

    fast_k = df['d_fast'].values
    slow_k = df['d_slow'].values

    return fast_k, slow_k


def STOCHRSI(data, period, k, d):
    df = data.copy()
    rsi = pd.DataFrame(RSI(df['close'], period))
    l = rsi.rolling(period).min()
    h = rsi.rolling(period).max()
    df['k_fast'] = 100 * (rsi - l) / (h - l)
    df['d_fast'] = MA(df['k_fast'], k)

    df['k_slow'] = df["d_fast"]
    df['d_slow'] = MA(df['k_slow'], d)

    fast_k = df['d_fast'].values
    slow_k = df['d_slow'].values

    return fast_k, slow_k


def BBANDS(data, ma_period, dev_val):
    middle = sma(data, ma_period)

    # calculating stddev. We won't count NaN values. Also NaNs are reasons not to use statistics.stddev, numpy, etc.
    stddevs = []
    real_data_cnt = 0
    
    for i in range(len(data)):
        if math.isnan(middle[i]):
            stddevs.append(0)
            real_data_cnt += 1
            continue

        if i-real_data_cnt >= ma_period:
            avg = sum(data[i-ma_period+1:i+1])/ma_period
            s = sum(map(lambda x: math.pow(x - avg,2), data[i-ma_period+1:i+1]))
            stddev_avg = s/ma_period
            stddev = math.sqrt(stddev_avg)
            stddevs.append(stddev)
        else:
           stddevs.append(0) 

    upper = []
    lower = []
    for i in range(len(middle)):
        if not math.isnan(middle[i]):
            upper.append(middle[i]+stddevs[i]*dev_val)
            lower.append(middle[i]-stddevs[i]*dev_val)
        else:
            upper.append(math.nan)
            lower.append(math.nan)

    return upper, middle, lower


def wwma(values, n):
    return values.ewm(alpha=1/n, adjust=False).mean()

# def atr(high, low, closes, n=14):
#     data['tr0'] = abs(high - low)
#     data['tr1'] = abs(high - closes.shift())
#     data['tr2'] = abs(low - closes.shift())
#     tr = data[['tr0', 'tr1', 'tr2']].max(axis=1)
#     atr = wwma(tr, n)
#     return atr



def REF(s, n=1):
    return pd.Series(s).shift(n).values

def AVEDEV(s, n):
    return pd.Series(s).rolling(n).apply(lambda x: (np.abs(x - x.mean())).mean()).values

def TR(high, low, closes):
    tr = np.maximum(np.maximum((high - low), np.abs(REF(closes, 1) - high)), np.abs(REF(closes, 1) - low))
    return tr

def ATR(high, low, closes, n):
    return MA(s=TR(high, low, closes), n=n)

def CCI(high, low, closes, n):
    tr = (high + low + closes) / 3
    return (tr-MA(s=tr, n=n)) / (0.015*AVEDEV(s=tr, n=n))
#https://github.com/mpquant/Python-Financial-Technical-Indicators-Pandas


# https://en.wikipedia.org/wiki/Money_flow_index
def MFI(high, low, closes, vol, period=14):
    typicals = []
    raw_money_flow = []
    money_flow_indexes = []

    for i in range(len(high)):
        typical = (high[i]+low[i]+closes[i])/3
        typicals.append(typical)

        raw_money_flow.append(typical*vol[i])

        total_positive = 0
        total_negative = 0

        money_flow_index = math.nan

        if i >= period:
            for pos, t in enumerate(typicals[i-period+1:i+1]):
                if t > typicals[i-period + pos]:
                    total_positive += raw_money_flow[i-period+pos+1]
                else:
                    total_negative += raw_money_flow[i-period+pos+1]

            if total_negative != 0:
                money_flow_ratio =total_positive/total_negative
            else:
                money_flow_ratio = 0

            money_flow_index = 100-100/(1+money_flow_ratio)
        money_flow_indexes.append(money_flow_index)
    return money_flow_indexes

def supertrend(df, period, atr_multiplier):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]

    return df

def EFI(data, n):
    previous_close = data['close'].shift(1).to_numpy()
    close = data['close'].to_numpy()
    volume = data['volume'].to_numpy()
    tr = (close - previous_close) * volume
    return EMA(tr, n)

def KAMA(data, n=38, fastend=2.5, slowend=1):
    price = data['close']
    absDiffx = abs(price - price.shift(1))
    ER_num = abs(price - price.shift(n))
    #ER_den = pd.stats.moments.rolling_sum(absDiffx,n)
    ER_den = pd.Series.rolling(absDiffx,n).sum()
    ER = ER_num / ER_den
    sc = (ER*(2.0/(fastend+1)-2.0/(slowend+1.0))+2/(slowend+1.0)) ** 2.0
    answer = np.zeros(sc.size)
    N = len(answer)
    first_value = True
    for i in range(N):
        if sc[i] != sc[i]:
            answer[i] = np.nan
        else:
            if first_value:
                answer[i] = price[i]
                first_value = False
            else:
                answer[i] = answer[i-1] + sc[i] * (price[i] - answer[i-1])
    return answer


def HA(df):
    ha_close = (df['open'] + df['close'] + df['high'] + df['low']) / 4

    ha_open = [(df['open'].iloc[0] + df['close'].iloc[0]) / 2]
    for close in ha_close[:-1]:
        ha_open.append((ha_open[-1] + close) / 2)
    ha_open = np.array(ha_open)

    elements = df['high'], df['low'], ha_open, ha_close
    ha_high, ha_low = np.vstack(elements).max(axis=0), np.vstack(elements).min(axis=0)

    return pd.DataFrame({
        'ha_open': ha_open,
        'ha_high': ha_high,
        'ha_low': ha_low,
        'ha_close': ha_close
    })

def QFL(
        data,
        N,
        M,
        hlc3,
        volume_ma: int = 6):

    # def which_order(list1):
    #     is_sorted_asc = all(a <= b for a, b in zip(list1, list1[1:]))
    #     is_sorted_desc = all(a >= b for a, b in zip(list1, list1[1:]))
    #     if not is_sorted_asc and not is_sorted_desc:
    #         order = None
    #     else:
    #         if is_sorted_asc:
    #             order = 'ASC'#возрастающий порядок
    #         if is_sorted_desc:
    #             order = 'DESC'#убывающий порядок
    #     return order

    result = base = 0
    #n_up = n_down = m_up = m_down = c_up = c_down =  False
    c_up = c_down = False

    ohlc = data.copy()
    # Считаем обьем скользящей средней
    #ohlc["volume_ma"] = ohlc["volume"].rolling(volume_ma).mean()

    # Считаем значение QFL сигнала
    if hlc3 == False:
        center_up = ohlc["low"].iloc[-(M+1)]
        m_up_array = [ohlc["low"].iloc[-i] for i in range(1, M+1)]
        n_up_array = [ohlc["low"].iloc[-i] for i in range(M+2, M+2+N)]

        center_down = ohlc["high"].iloc[-(M+1)]
        m_down_array = [ohlc["high"].iloc[-i] for i in range(1, M+1)]
        n_down_array = [ohlc["high"].iloc[-i] for i in range(M+2, M+2+N)]

        n_up_array = list(reversed(n_up_array))
        n_down_array = list(reversed(n_down_array))
        m_up_array = list(reversed(m_up_array))
        m_down_array = list(reversed(m_down_array))

    # hl version
    else:
        center_hlc3 = round((ohlc["high"].iloc[-(M+1)]+ohlc["low"].iloc[-(M+1)]+ohlc["close"].iloc[-(M+1)])/3,2)
        m_array_hlc3 = [round((x + y + z)/3,2) for x, y, z in zip([ohlc["high"].iloc[-i] for i in range(1, M+1)], [ohlc["low"].iloc[-i] for i in range(1, M+1)], [ohlc["close"].iloc[-i] for i in range(1, M+1)])]
        n_array_hlc3 = [round((x + y + z)/3,2) for x, y, z in zip([ohlc["high"].iloc[-i] for i in range(M+2, M+2+N)], [ohlc["low"].iloc[-i] for i in range(M+2, M+2+N)], [ohlc["close"].iloc[-i] for i in range(M+2, M+2+N)])]

        n_up_array = n_down_array = n_array_hlc3
        m_up_array = m_down_array = m_array_hlc3
        base = center_up = center_down = center_hlc3



    # if N > 1:
    #     if which_order(n_up_array) == 'DESC':
    #         n_up = True
    #     if which_order(n_down_array) == 'ASC':
    #         n_down = True
    # else:
    #     n_up = n_down = True
    #
    # if M > 1:
    #     if which_order(m_up_array) == 'ASC':
    #         m_up = True
    #     if which_order(m_down_array) == 'DESC':
    #         m_down = True
    # else:
    #     m_up = m_down = True

    all_up_array = n_up_array + m_up_array
    all_down_array = n_down_array + m_down_array

    if center_up < min(all_up_array):
        c_up = True
    if center_down > max(all_down_array):
        c_down = True

    # if n_up == True and m_up == True and center_up < n_up_array[-1] and center_up < m_up_array[0]:
    #     c_up = True
    # elif n_down == True and m_down == True and center_down > n_down_array[-1] and center_down > m_down_array[0]:
    #     c_down = True
    # else:
    #     c_up = c_down = False

    if c_up == True:
        result = 'buy'
        base = center_up
    if c_down == True:
        result = 'sell'
        base = center_down

    # if result == 'buy':
    #     print('buy signal found with base:', base)
    # if result == 'sell':
    #     print('sell signal found with base:', base)

    return result, base