import tkinter as tk
#import time #TRIAL
import re
import os
import sqlite3
from tkinter import ttk, Text, DISABLED, NORMAL, messagebox, font
import tkinter.scrolledtext as tkst
from bot.defines import LANGUAGES, APP_NAME, APP_VERSION, APP_AUTHOR, APP_WEBSITE, APP_MARKET, APP_EXCHANGE, APP_NOTE
from bot.kernel import Connector
import asyncio

FONT_FAMILY = "Arial"
FONT_SIZE = 8
FONT_COLOR = "#339999"
SELECT_BACKGROUND = "#aaaaaa"
#now = time.time() #TRIAL

class CreateToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.waittime = 50  # miliseconds
        self.wraplength = 300  # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 15
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffff", relief='solid', borderwidth=1,
                         wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()

class Gui(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
 
        # Variables
        self.exchange = tk.StringVar()
        self.grow_first = tk.BooleanVar()
        self.percent_or_amount = tk.BooleanVar()
        self.can_spend = tk.DoubleVar()
        self.bo_amount = tk.DoubleVar()
        #self.so_amount = tk.DoubleVar()
        self.leverage = tk.StringVar()
        self.martingale = tk.DoubleVar()
        self.first_so_coeff = tk.DoubleVar()
        self.dynamic_so_coeff = tk.DoubleVar()

        self.first_step = tk.DoubleVar()
        self.lift_step = tk.DoubleVar()
        self.range_cover = tk.DoubleVar()

        self.margin_mode = tk.StringVar()

        self.select_profit_variants = []
        self.take_profit = tk.StringVar()

        self.squeeze_profit = tk.DoubleVar()
        self.trailing_stop = tk.DoubleVar()
        self.limit_stop = tk.DoubleVar()

        self.use_dynamic_so = tk.BooleanVar()

        #self.log_distribution = tk.BooleanVar()
        #self.log_coeff = tk.DoubleVar()
        self.orders_total = tk.IntVar()
        self.active_orders = tk.IntVar()
        self.time_sleep = tk.IntVar()
        self.time_sleep_coeff = tk.IntVar()
        #self.one_or_more_variants = []
        #self.one_or_more = tk.BooleanVar()
        self.algorithm = tk.StringVar()
        #self.bottype = tk.StringVar()
        self.market = tk.StringVar()
        self.base_coin = tk.StringVar()
        self.quote_coin = tk.StringVar()
        self.pair_1 = tk.StringVar()
        self.pair_2 = tk.StringVar()
        self.lang = tk.StringVar()
        self.cancel_on_trend = tk.BooleanVar()

        self.global_timeframe = tk.StringVar()

        # self.entry_qfl_N = tk.IntVar()
        # self.entry_qfl_M = tk.IntVar()
        # self.entry_qfl_h_l_percent = tk.DoubleVar()
        # self.avg_qfl_N = tk.IntVar()
        # self.avg_qfl_M = tk.IntVar()
        # self.avg_qfl_h_l_percent = tk.DoubleVar()
        # self.exit_qfl_N = tk.IntVar()
        # self.exit_qfl_M = tk.IntVar()
        # self.exit_qfl_h_l_percent = tk.DoubleVar()
        # self.entry_qfl_u_o = tk.StringVar()
        # self.avg_qfl_u_o = tk.StringVar()
        # self.exit_qfl_u_o = tk.StringVar()
        # self.entry_qfl_u_o_variants = []
        # self.avg_qfl_u_o_variants = []
        # self.exit_qfl_u_o_variants = []







        # CCI_CROSS PRESET
        self.entry_cci_cross_long = tk.IntVar()
        self.entry_cci_cross_short = tk.IntVar()
        self.avg_cci_cross_long = tk.IntVar()
        self.avg_cci_cross_short = tk.IntVar()
        self.exit_cci_cross_long = tk.IntVar()
        self.exit_cci_cross_short = tk.IntVar()
        self.entry_cci_cross_use_price = tk.BooleanVar()
        self.avg_cci_cross_use_price = tk.BooleanVar()
        self.exit_cci_cross_use_price = tk.BooleanVar()

        # self.entry_cci_cross_u_o_variants = []
        # self.entry_cci_cross_u_o = tk.StringVar()
        # self.avg_cci_cross_u_o_variants = []
        # self.avg_cci_cross_u_o = tk.StringVar()
        # self.exit_cci_cross_u_o_variants = []
        # self.exit_cci_cross_u_o = tk.StringVar()

        # MA PRESET
        self.entry_sma1_length = tk.IntVar()
        self.avg_sma1_length = tk.IntVar()
        self.exit_sma1_length = tk.IntVar()
        self.entry_sma2_length = tk.IntVar()
        self.avg_sma2_length = tk.IntVar()
        self.exit_sma2_length = tk.IntVar()

        self.entry_ma1_cross_length = tk.IntVar()
        self.entry_ma2_cross_length = tk.IntVar()
        self.avg_ma1_cross_length = tk.IntVar()
        self.avg_ma2_cross_length = tk.IntVar()
        self.exit_ma1_cross_length = tk.IntVar()
        self.exit_ma2_cross_length = tk.IntVar()

        # self.entry_ma_cross_u_o_variants = []
        # self.entry_ma_cross_u_o = tk.StringVar()
        # self.avg_ma_cross_u_o_variants = []
        # self.avg_ma_cross_u_o = tk.StringVar()
        # self.exit_ma_cross_u_o_variants = []
        # self.exit_ma_cross_u_o = tk.StringVar()

        # SMA_RSI PRESET
        self.entry_smarsi_cross_up_long = tk.IntVar()
        self.entry_smarsi_cross_low_long = tk.IntVar()
        self.entry_smarsi_cross_up_short = tk.IntVar()
        self.entry_smarsi_cross_low_short = tk.IntVar()
        # self.entry_smarsi_cross_length = tk.IntVar()

        self.avg_smarsi_cross_up_long = tk.IntVar()
        self.avg_smarsi_cross_low_long = tk.IntVar()
        self.avg_smarsi_cross_up_short = tk.IntVar()
        self.avg_smarsi_cross_low_short = tk.IntVar()
        # self.avg_smarsi_cross_length = tk.IntVar()

        self.exit_smarsi_cross_up_long = tk.IntVar()
        self.exit_smarsi_cross_low_long = tk.IntVar()
        self.exit_smarsi_cross_up_short = tk.IntVar()
        self.exit_smarsi_cross_low_short = tk.IntVar()
        # self.exit_smarsi_cross_length = tk.IntVar()

        #PRESET SELECTION
        self.entry_preset_variants = []
        self.entry_preset = tk.StringVar()
        self.entry_by_indicators = tk.BooleanVar()
        self.entry_timeframe = tk.StringVar()

        self.avg_preset_variants = []
        self.avg_preset = tk.StringVar()
        self.timeframe = tk.StringVar()
        self.avg_use_tf_switching = tk.BooleanVar()

        self.exit_preset_variants = []
        self.exit_preset = tk.StringVar()
        self.exit_timeframe = tk.StringVar()
        self.exit_use_tv_signals = tk.BooleanVar()

        # CCI
        # ENTRY STOCH_CCI PRESET
        self.entry_use_stoch = tk.BooleanVar()
        self.entry_use_cci = tk.BooleanVar()
        self.entry_basic_indicator = tk.StringVar()
        self.entry_stoch_up_long = tk.IntVar()
        self.entry_stoch_low_long = tk.IntVar()
        self.entry_stoch_up_short = tk.IntVar()
        self.entry_stoch_low_short = tk.IntVar()
        self.entry_cci_long = tk.IntVar()
        self.entry_cci_short = tk.IntVar()

        # AVG STOCH_CCI PRESET
        self.avg_use_stoch = tk.BooleanVar()
        self.avg_use_cci = tk.BooleanVar()
        self.avg_basic_indicator = tk.StringVar()
        self.avg_stoch_up_long = tk.IntVar()
        self.avg_stoch_low_long = tk.IntVar()
        self.avg_stoch_up_short = tk.IntVar()
        self.avg_stoch_low_short = tk.IntVar()
        self.avg_cci_long = tk.IntVar()
        self.avg_cci_short = tk.IntVar()

        # EXIT STOCH_CCI PRESET
        self.exit_use_stoch = tk.BooleanVar()
        self.exit_use_cci = tk.BooleanVar()
        self.exit_basic_indicator = tk.StringVar()
        self.exit_stoch_up_long = tk.IntVar()
        self.exit_stoch_low_long = tk.IntVar()
        self.exit_stoch_up_short = tk.IntVar()
        self.exit_stoch_low_short = tk.IntVar()
        self.exit_cci_long = tk.IntVar()
        self.exit_cci_short = tk.IntVar()

        # RSI
        # ENTRY STOCH_RSI PRESET
        self.entry_rsi_use_stoch = tk.BooleanVar()
        self.entry_rsi_use_rsi = tk.BooleanVar()
        self.entry_rsi_basic_indicator = tk.StringVar()
        self.entry_rsi_stoch_up_long = tk.IntVar()
        self.entry_rsi_stoch_low_long = tk.IntVar()
        self.entry_rsi_stoch_up_short = tk.IntVar()
        self.entry_rsi_stoch_low_short = tk.IntVar()
        self.entry_rsi_long = tk.IntVar()
        self.entry_rsi_short = tk.IntVar()

        # AVG STOCH_RSI PRESET
        self.avg_rsi_use_stoch = tk.BooleanVar()
        self.avg_rsi_use_rsi = tk.BooleanVar()
        self.avg_rsi_basic_indicator = tk.StringVar()
        self.avg_rsi_stoch_up_long = tk.IntVar()
        self.avg_rsi_stoch_low_long = tk.IntVar()
        self.avg_rsi_stoch_up_short = tk.IntVar()
        self.avg_rsi_stoch_low_short = tk.IntVar()
        self.avg_rsi_long = tk.IntVar()
        self.avg_rsi_short = tk.IntVar()

        # EXIT STOCH_RSI PRESET
        self.exit_rsi_use_stoch = tk.BooleanVar()
        self.exit_rsi_use_rsi = tk.BooleanVar()
        self.exit_rsi_basic_indicator = tk.StringVar()
        self.exit_rsi_stoch_up_long = tk.IntVar()
        self.exit_rsi_stoch_low_long = tk.IntVar()
        self.exit_rsi_stoch_up_short = tk.IntVar()
        self.exit_rsi_stoch_low_short = tk.IntVar()
        self.exit_rsi_long = tk.IntVar()
        self.exit_rsi_short = tk.IntVar()

        # PRICE PRESET
        self.entry_price_delta_long = tk.DoubleVar()
        self.entry_price_delta_short = tk.DoubleVar()
        self.avg_price_delta_long = tk.DoubleVar()
        self.avg_price_delta_short = tk.DoubleVar()

        # PROFIT
        self.exit_profit_level = tk.DoubleVar()
        self.exit_stop_loss_level = tk.DoubleVar()

        self.empty_label_1 = tk.StringVar()
        self.empty_label_2 = tk.StringVar()
        self.empty_label_3 = tk.StringVar()
        self.empty_label_4 = tk.StringVar()
        self.empty_label_5 = tk.StringVar()
        self.empty_label_6 = tk.StringVar()

        # USE GLOBAL_STOCH
        self.use_global_stoch = tk.BooleanVar()
        self.global_stoch_up_long = tk.IntVar()
        self.global_stoch_low_long = tk.IntVar()
        self.global_stoch_up_short = tk.IntVar()
        self.global_stoch_low_short = tk.IntVar()

        self.use_stoch_rsi = tk.BooleanVar()
        self.stoch_fastk_period = tk.IntVar()
        self.stoch_slowk_period = tk.IntVar()
        self.stoch_slowd_period = tk.IntVar()
        self.cci_length = tk.IntVar()
        self.ema200 = tk.IntVar()
        self.ema200_delta = tk.DoubleVar()
        self.macd_f = tk.IntVar()
        self.macd_s = tk.IntVar()
        self.macd_signal = tk.IntVar()
        self.rsi_length = tk.IntVar()
        #self.smarsi_length = tk.IntVar()
        self.atr_length = tk.IntVar()
        self.efi_length = tk.IntVar()
        self.bb_period = tk.IntVar()
        self.bb_dev = tk.IntVar()
        #self.supertrend_period = tk.IntVar()
        #self.supertrend_multiplier = tk.IntVar()

        self.ema_global_switch = tk.BooleanVar()
        self.orders_switch = tk.BooleanVar()
        self.orders_count = tk.IntVar()
        self.last_candle_switch = tk.BooleanVar()
        self.last_candle_count = tk.IntVar()
        self.last_candle_orders = tk.IntVar()
        self.stoch_adjustment = tk.IntVar()

        #self.immediate_so = tk.BooleanVar()
        self.so_safety_price = tk.DoubleVar()
        self.emergency_averaging = tk.DoubleVar()
        self.back_profit = tk.DoubleVar()
        self.use_margin = tk.BooleanVar()
        self.margin_top = tk.DoubleVar()
        self.margin_bottom = tk.DoubleVar()

        #self.exchange_timeframes = []


        master.title('%s, %s (%s) :: %s %s' % (APP_EXCHANGE, APP_MARKET, APP_NOTE, APP_NAME, APP_VERSION))

        master.geometry("1024x735")
        master.iconbitmap('icon.ico')


        # Rows
        self.general = tk.Frame(master)
        self.general.grid(row=0, sticky="W")

        self.strategy = tk.Frame(master)
        self.strategy.grid(row=1, sticky="W")

        self.advanced = tk.Frame(master)
        self.advanced.grid(row=2, sticky="W")

        self.row_31 = tk.Frame(master)
        self.row_31.grid(row=3, sticky="WS")

        # self.row_32 = tk.Frame(master)
        # self.row_32.pack(pady=25, anchor=tk.W)
        self.row_32 = tk.Frame(master)
        #self.all_buttons = tk.Frame(self.row_32, height=150)
        self.row_32.grid(row=4, sticky="WS", pady=10)

        self.general_left = tk.Frame(self.general, width=150)
        self.general_separator_1 = tk.Frame(self.general, width=32)
        self.general_center = tk.Frame(self.general, width=220)
        self.general_separator_2 = tk.Frame(self.general, width=40)
        self.general_right = tk.Frame(self.general, width=150)
        self.general_left.grid(row=0, column=0, sticky="WN")
        self.general_separator_1.grid(row=0, column=1, sticky="WN")
        self.general_center.grid(row=0, column=2, sticky="WN")
        self.general_separator_2.grid(row=0, column=3, sticky="WN")
        self.general_right.grid(row=0, column=4, sticky="WN")

        self.strategy_left = tk.Frame(self.strategy, width=150)
        self.strategy_separator_1 = tk.Frame(self.strategy, width=37)
        self.strategy_center = tk.Frame(self.strategy, width=220)
        self.strategy_separator_2 = tk.Frame(self.strategy, width=45)
        self.strategy_right = tk.Frame(self.strategy, width=150)
        self.strategy_left.grid(row=0, column=0, sticky="WN")
        self.strategy_separator_1.grid(row=0, column=1, sticky="WN")
        self.strategy_center.grid(row=0, column=2, sticky="WN")
        self.strategy_separator_2.grid(row=0, column=3, sticky="WN")
        self.strategy_right.grid(row=0, column=4, sticky="WN")

        self.advanced_left = tk.Frame(self.advanced, width=150)
        self.advanced_separator_1 = tk.Frame(self.advanced, width=43)
        self.advanced_center = tk.Frame(self.advanced, width=220)
        self.advanced_separator_2 = tk.Frame(self.advanced, width=45)
        self.advanced_right = tk.Frame(self.advanced, width=150)
        self.advanced_left.grid(row=0, column=0, sticky="WN")
        self.advanced_separator_1.grid(row=0, column=1, sticky="WN")
        self.advanced_center.grid(row=0, column=2, sticky="WN")
        self.advanced_separator_2.grid(row=0, column=3, sticky="WN")
        self.advanced_right.grid(row=0, column=4, sticky="WN")

        # General settings
        self.general_settings_label = tk.Label(self.general_left, width=23, padx=10, pady=5, anchor=tk.W, font="Tahoma 8 bold")
        self.general_settings_label.grid(column=0, row=0, columnspan=2, sticky="W")

        # Bot type
        # self.bottype_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        # self.bottype_label.grid(column=0, row=1, sticky="W", pady=2)
        # self.bottype_long_select = tk.Radiobutton(self.general_left, text="Single", variable=self.bottype, value='single', padx=5, pady=2, command=lambda: self.bottype_handle(self.bottype.get()))
        # self.bottype_long_select.grid(column=1, row=1, sticky="W")
        # self.bottype_short_select = tk.Radiobutton(self.general_left, text="Multi", variable=self.bottype, value='multi', padx=6, pady=2, command=lambda: self.bottype_handle(self.bottype.get()))
        # self.bottype_short_select.grid(column=2, columnspan=3, row=1, sticky="W")

        #Pair
        self.base_coin_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        self.base_coin_label.grid(column=0, row=2, sticky="W", pady=2)
        self.base_coin_entry = tk.Entry(self.general_left, width=10, textvariable=self.base_coin)  ########### state=DISABLED
        self.base_coin_entry.grid(column=1, row=2, sticky="W", padx=5)
        self.separator_label = tk.Label(self.general_left, width=1, anchor=tk.W)
        self.separator_label.grid(column=2, row=2, sticky="W", padx=3)
        self.quote_coin_entry = tk.Entry(self.general_left, width=6, textvariable=self.quote_coin)
        self.quote_coin_entry.grid(column=3, row=2, sticky="W", padx=3)

        # Select algorithm
        self.algorithm_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        #self.algorithm_label.grid(column=0, row=3, sticky="W", pady=2)
        #self.algorithm_long_select = tk.Radiobutton(self.general_left, text="Long", variable=self.algorithm, value='long', padx=5, pady=2, command=lambda: self.select_algorithm_handle(self.algorithm.get()))
        #self.algorithm_long_select.grid(column=1, row=3, sticky="W", padx=5)
        #self.algorithm_short_select = tk.Radiobutton(self.general_left, text="Short", variable=self.algorithm, value='short', pady=2, command=lambda: self.select_algorithm_handle(self.algorithm.get()))
        #self.algorithm_short_select.grid(column=2, columnspan=3, row=3, sticky="W", padx=5)

        # What coin to increase
        self.grow_first_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        #self.grow_first_label.grid(column=0, row=4, sticky="W", pady=2)
        #self.grow_first_yes = tk.Radiobutton(self.general_left, text="1       ", variable=self.grow_first, value=True, padx=5, command=lambda: self.grow_first_handle(self.grow_first.get()))
        #self.grow_first_yes.grid(column=1, row=4, sticky="W", padx=5)
        #self.grow_first_no = tk.Radiobutton(self.general_left, text="2", variable=self.grow_first, value=False, padx=2, pady=2, command=lambda: self.grow_first_handle(self.grow_first.get()))
        #self.grow_first_no.grid(column=2, columnspan=3, row=4, sticky="W", padx=4)

        # Depo
        self.can_spend_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        self.can_spend_label.grid(column=0, row=5, sticky="W", pady=2)
        self.can_spend_entry = tk.Entry(self.general_left, width=10, textvariable=self.can_spend)
        self.can_spend_entry.grid(column=1, row=5, sticky="W", padx=5)
        self.percent_or_amount_label = tk.Label(self.general_left, width=2, anchor=tk.W)
        self.percent_or_amount_label.grid(column=2, columnspan=3, row=5, sticky="W")
        self.percent_or_amount_checkbutton = tk.Checkbutton(self.general_left, variable=self.percent_or_amount, onvalue=1, offvalue=0, padx=1, command=lambda: self.percent_or_amount_handle(self.percent_or_amount.get()))
        self.percent_or_amount_checkbutton.grid(column=3, row=5, sticky="W", padx=2)
        self.percent_or_amount_status_label = tk.Label(self.general_left, anchor=tk.W)
        self.percent_or_amount_status_label.grid(column=3, row=5, sticky="W")

        # BO_AMOUNT
        self.bo_amount_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        self.bo_amount_label.grid(column=0, row=6, sticky="W", pady=2)
        self.bo_amount_entry = tk.Entry(self.general_left, width=10, textvariable=self.bo_amount)
        self.bo_amount_entry.grid(column=1, row=6, sticky="W", padx=5)

        # SO_AMOUNT
        #self.so_amount_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        #self.so_amount_label.grid(column=0, row=7, sticky="W", pady=2)
        #self.so_amount_entry = tk.Entry(self.general_left, width=10, textvariable=self.so_amount)
        #self.so_amount_entry.grid(column=1, row=7, sticky="W", padx=5)

        # LEVERAGE
        self.leverage_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        self.leverage_label.grid(column=0, row=7, sticky="W", pady=2)
        self.leverage_entry = tk.Entry(self.general_left, width=10, textvariable=self.leverage)
        self.leverage_entry.grid(column=1, row=7, sticky="W", padx=5)

        # MARGIN_MODE
        self.margin_mode_label = tk.Label(self.general_left, width=23, padx=10, anchor=tk.W)
        self.margin_mode_label.grid(column=0, row=8, sticky="W", pady=2)
        self.margin_mode_list_box = ttk.OptionMenu(self.general_left, variable=self.margin_mode, style="TMenubutton", command=lambda event: self.margin_mode_handle(self.margin_mode.get()))
        self.margin_mode_list_box.grid(column=1, columnspan=3, row=8, sticky="W", padx=5)


        # Static or Dynamic
        self.empty_label_1 = tk.Label(self.general_center, width=24, padx=10, pady=2, anchor=tk.W)
        self.empty_label_1.grid(column=0, row=0, columnspan=2, sticky="W")
        self.use_dynamic_so_label = tk.Label(self.general_center, width=24, padx=5, anchor=tk.W)
        # self.use_dynamic_so_label.grid(column=0, row=1, sticky="W", pady=3)
        # self.use_dynamic_so_yes = tk.Radiobutton(self.general_center, text="yes", variable=self.use_dynamic_so, value=True, padx=5, pady=2, command=lambda: self.use_dynamic_so_handle(self.use_dynamic_so.get()))
        # self.use_dynamic_so_yes.grid(column=1, row=1, sticky="W")
        # self.use_dynamic_so_no = tk.Radiobutton(self.general_center, text="no", variable=self.use_dynamic_so, value=False, padx=5, pady=2, command=lambda: self.use_dynamic_so_handle(self.use_dynamic_so.get()))
        # self.use_dynamic_so_no.grid(column=2, row=1, sticky="W")

        # First step indentation
        self.first_step_label = tk.Label(self.general_center, width=24, anchor=tk.W)
        self.first_step_label.grid(column=0, row=2, sticky="W", padx=5, pady=2)
        self.first_step_entry = tk.Entry(self.general_center, textvariable=self.first_step)
        self.first_step_entry.grid(column=1, row=2, columnspan=2, sticky="W")

        # Indent for orders re-place (lift_step)
        self.lift_step_label = tk.Label(self.general_center, width=24, anchor=tk.W)
        self.lift_step_label.grid(column=0, row=3, sticky="W", padx=5, pady=2)
        self.lift_step_entry = tk.Entry(self.general_center, textvariable=self.lift_step)
        self.lift_step_entry.grid(column=1, columnspan=2, row=3, sticky="W")

        # Overlap price
        self.range_cover_label = tk.Label(self.general_center, width=24, anchor=tk.W)
        self.range_cover_label.grid(column=0, row=4, sticky="W", padx=5, pady=2)
        self.range_cover_entry = tk.Entry(self.general_center, textvariable=self.range_cover)
        self.range_cover_entry.grid(column=1, columnspan=2, row=4, sticky="W")

        # Orders total
        self.orders_total_label = tk.Label(self.general_center, width=24, anchor=tk.W)
        self.orders_total_label.grid(column=0, row=5, sticky="W", padx=5, pady=3)
        self.orders_total_entry = tk.Entry(self.general_center, textvariable=self.orders_total)
        self.orders_total_entry.grid(column=1, columnspan=2, row=5, sticky="W")

        # Active Orders
        self.active_orders_label = tk.Label(self.general_center, width=24, anchor=tk.W)
        self.active_orders_label.grid(column=0, row=6, sticky="W", padx=5, pady=2)
        self.active_orders_entry = tk.Entry(self.general_center, textvariable=self.active_orders)
        self.active_orders_entry.grid(column=1, columnspan=2, row=6, sticky="W")

        self.empty_label_1 = tk.Label(self.general_right, width=24, padx=10, pady=2, anchor=tk.W)
        self.empty_label_1.grid(column=0, row=0, columnspan=3, sticky="W")

        # DCA for Static mode
        #self.log_distribution_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        #self.log_distribution_yes = tk.Radiobutton(self.general_right, text="yes", variable=self.log_distribution, value=True, padx=3, pady=1, command=lambda: self.log_distribution_handle(self.log_distribution.get()))
        #self.log_distribution_no = tk.Radiobutton(self.general_right, text="no", variable=self.log_distribution, value=False, padx=1, pady=1, command=lambda: self.log_distribution_handle(self.log_distribution.get()))

        #self.log_coeff_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        #self.log_coeff_entry = tk.Entry(self.general_right, width=19, textvariable=self.log_coeff)

        #self.one_or_more_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        #self.one_or_more_yes = tk.Radiobutton(self.general_right, text="one", variable=self.one_or_more, value=True, padx=3, pady=1, command=lambda: self.one_or_more_handle(self.one_or_more.get()))
        #self.one_or_more_no = tk.Radiobutton(self.general_right, text="grid", variable=self.one_or_more, value=False, padx=1, pady=1, command=lambda: self.one_or_more_handle(self.one_or_more.get()))

        #self.one_or_more_list_box = ttk.OptionMenu(self.general_right, variable=self.one_or_more, style="TMenubutton", command=lambda event: self.one_or_more_handle(self.one_or_more.get()))

        self.martingale_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        self.martingale_label.grid(column=0, row=1, sticky="W", padx=4, pady=2)
        self.martingale_entry = tk.Entry(self.general_right, width=19, textvariable=self.martingale)
        self.martingale_entry.grid(column=1, columnspan=2, row=1, sticky="E", padx=5)

        # first CO koeff
        self.first_so_coeff_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        self.first_so_coeff_label.grid(column=0, row=2, sticky="W", padx=4, pady=2)
        self.first_so_coeff_entry = tk.Entry(self.general_right, width=19, textvariable=self.first_so_coeff)
        self.first_so_coeff_entry.grid(column=1, columnspan=2, row=2, sticky="E", padx=5)

        # dynamic CO koeff
        self.dynamic_so_coeff_label = tk.Label(self.general_right, width=24, anchor=tk.W)
        self.dynamic_so_coeff_label.grid(column=0, row=3, sticky="W", padx=4, pady=2)
        self.dynamic_so_coeff_entry = tk.Entry(self.general_right, width=19, textvariable=self.dynamic_so_coeff)
        self.dynamic_so_coeff_entry.grid(column=1, columnspan=2, row=3, sticky="E", padx=5)

        # Time sleep
        self.time_sleep_label = tk.Label(self.general_right, width=24, padx=5, anchor=tk.W)
        self.time_sleep_label.grid(column=0, row=4, sticky="W", pady=3)
        self.time_sleep_entry = tk.Entry(self.general_right, width=8, textvariable=self.time_sleep)
        self.time_sleep_entry.grid(column=1, columnspan=2, row=4, sticky="W", padx=4, pady=3)
        self.time_sleep_coeff_entry = tk.Entry(self.general_right, width=8, textvariable=self.time_sleep_coeff)
        self.time_sleep_coeff_entry.grid(column=2, columnspan=2, row=4, sticky="E", padx=5)

        self.cancel_on_trend_label = tk.Label(self.general_right, width=24, padx=5, anchor=tk.W)
        self.cancel_on_trend_label.grid(column=0, row=5, sticky="W", pady=2)
        self.cancel_on_trend_yes = tk.Radiobutton(self.general_right, text="yes", variable=self.cancel_on_trend, value=True, padx=3, pady=2, command=lambda: self.cancel_on_trend_handle(self.cancel_on_trend.get()))
        self.cancel_on_trend_yes.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
        self.cancel_on_trend_no = tk.Radiobutton(self.general_right, text="no", variable=self.cancel_on_trend, value=False, padx=3, pady=2, command=lambda: self.cancel_on_trend_handle(self.cancel_on_trend.get()))
        self.cancel_on_trend_no.grid(column=2, columnspan=2, row=5, sticky="E", padx=5)

        # ENTRY AVERAGING EXIT
        self.entry_conditions_label = tk.Label(self.strategy_left, width=23, padx=10, pady=5, anchor=tk.W, font="Tahoma 8 bold")
        self.entry_conditions_label.grid(column=0, row=0, columnspan=3, sticky="W")

        # ENTRY
        self.entry_by_indicators_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_by_indicators_label.grid(column=0, row=1, sticky="W", pady=2)
        self.entry_by_indicators_yes = tk.Radiobutton(self.strategy_left, text="yes", variable=self.entry_by_indicators, value=True, padx=5, pady=2, command=lambda: self.entry_by_indicators_handle(self.entry_by_indicators.get()))
        self.entry_by_indicators_yes.grid(column=1, row=1, sticky="W", padx=5)
        self.entry_by_indicators_no = tk.Radiobutton(self.strategy_left, text="no", variable=self.entry_by_indicators, value=False, padx=3, pady=2, command=lambda: self.entry_by_indicators_handle(self.entry_by_indicators.get()))
        self.entry_by_indicators_no.grid(column=2, row=1, sticky="E", padx=5)
        self.empty_label_2 = tk.Label(self.strategy_left, width=23, padx=10, pady=0, anchor=tk.W)
        self.empty_label_3 = tk.Label(self.strategy_left, width=18, padx=2, pady=0, anchor=tk.W)
        #self.empty_label_1.grid(column=3, row=1, sticky="E", padx=5)

        om_style = ttk.Style()
        om_style.configure("TMenubutton", background="white", foreground="black", width=15)



        self.entry_timeframe_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        #self.entry_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
        self.entry_timeframe_entry = tk.Entry(self.strategy_left, textvariable=self.entry_timeframe)
        #self.entry_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)

        self.entry_preset_label = tk.Label(self.strategy_left, width=23, padx=10, pady=2, anchor=tk.W)
        #self.entry_preset_label.grid(column=0, row=3, sticky="W", pady=2)
        self.entry_preset_list_box = ttk.OptionMenu(self.strategy_left, variable=self.entry_preset, style="TMenubutton", command=lambda event: self.entry_preset_handle(self.entry_preset.get()))
        #self.entry_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)


        self.entry_cci_cross_use_price_label = tk.Label(self.strategy_left, width=23, padx=10, pady=2, anchor=tk.W)
        #self.entry_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=2)
        self.entry_cci_cross_use_price_yes = tk.Radiobutton(self.strategy_left, text="yes", variable=self.entry_cci_cross_use_price, value=True, padx=5, pady=2, command=lambda: self.entry_cci_cross_use_price_handle(self.entry_cci_cross_use_price.get()))
        #self.entry_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=5)
        self.entry_cci_cross_use_price_no = tk.Radiobutton(self.strategy_left, text="no", variable=self.entry_cci_cross_use_price, value=False, padx=7, pady=2, command=lambda: self.entry_cci_cross_use_price_handle(self.entry_cci_cross_use_price.get()))
        #self.entry_cci_cross_use_price_no.grid(column=2, row=4, sticky="W")

        # ENTRY for cci_cross preset
        self.entry_cci_cross_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_cci_cross_long)
        self.entry_cci_cross_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_cci_cross_short)

        #self.entry_cci_cross_u_o_label = tk.Label(self.strategy_left, width=23, padx=10, pady=2, anchor=tk.W)
        #self.entry_cci_cross_u_o_list_box = ttk.OptionMenu(self.strategy_left, variable=self.entry_cci_cross_u_o, style="TMenubutton", command=lambda event: self.entry_cci_cross_u_o_handle(self.entry_cci_cross_u_o.get()))


        # CCI
        # STOCH_CCI
        self.entry_use_stoch_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_use_stoch_checkbutton = tk.Checkbutton(self.strategy_left, variable=self.entry_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.entry_use_stoch_or_cci_handle(self.entry_basic_indicator.get(), self.entry_use_stoch.get(), self.entry_use_cci.get()))
        self.entry_use_stoch_status_label = tk.Label(self.strategy_left, anchor=tk.W)
        self.entry_use_cci_checkbutton = tk.Checkbutton(self.strategy_left, variable=self.entry_use_cci, text="cci", onvalue=1, offvalue=0, command=lambda: self.entry_use_stoch_or_cci_handle(self.entry_basic_indicator.get(), self.entry_use_stoch.get(), self.entry_use_cci.get()))
        self.entry_use_cci_status_label = tk.Label(self.strategy_left, anchor=tk.W)
        self.entry_basic_indicator_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_basic_indicator_stoch = tk.Radiobutton(self.strategy_left, text="stoch", variable=self.entry_basic_indicator, value='stoch', padx=5, pady=2, command=lambda: self.entry_basic_indicator_handle(self.entry_basic_indicator.get(), self.entry_use_stoch.get(), self.entry_use_cci.get()))
        self.entry_basic_indicator_cci = tk.Radiobutton(self.strategy_left, text="cci", variable=self.entry_basic_indicator, value='cci', padx=7, pady=2, command=lambda: self.entry_basic_indicator_handle(self.entry_basic_indicator.get(), self.entry_use_stoch.get(), self.entry_use_cci.get()))
        self.entry_stoch_up_long_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_stoch_up_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_stoch_up_long)
        self.entry_stoch_low_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_stoch_low_long)
        self.entry_stoch_up_short_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_stoch_up_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_stoch_up_short)
        self.entry_stoch_low_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_stoch_low_short)
        self.entry_cci_level_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_cci_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_cci_long)
        self.entry_cci_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_cci_short)

        # RSI
        # STOCH_RSI
        self.entry_rsi_use_stoch_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_rsi_use_stoch_checkbutton = tk.Checkbutton(self.strategy_left, variable=self.entry_rsi_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.entry_use_stoch_or_rsi_handle(self.entry_rsi_basic_indicator.get(), self.entry_rsi_use_stoch.get(), self.entry_rsi_use_rsi.get()))
        self.entry_rsi_use_stoch_status_label = tk.Label(self.strategy_left, anchor=tk.W)
        self.entry_rsi_use_rsi_checkbutton = tk.Checkbutton(self.strategy_left, variable=self.entry_rsi_use_rsi, text="rsi", onvalue=1, offvalue=0, command=lambda: self.entry_use_stoch_or_rsi_handle(self.entry_rsi_basic_indicator.get(), self.entry_rsi_use_stoch.get(), self.entry_rsi_use_rsi.get()))
        self.entry_rsi_use_rsi_status_label = tk.Label(self.strategy_left, anchor=tk.W)
        self.entry_rsi_basic_indicator_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_rsi_basic_indicator_stoch = tk.Radiobutton(self.strategy_left, text="stoch", variable=self.entry_rsi_basic_indicator, value='stoch', padx=5, pady=2, command=lambda: self.entry_rsi_basic_indicator_handle(self.entry_rsi_basic_indicator.get(), self.entry_rsi_use_stoch.get(), self.entry_rsi_use_rsi.get()))
        self.entry_rsi_basic_indicator_rsi = tk.Radiobutton(self.strategy_left, text="rsi", variable=self.entry_rsi_basic_indicator, value='rsi', padx=7, pady=2, command=lambda: self.entry_rsi_basic_indicator_handle(self.entry_rsi_basic_indicator.get(), self.entry_rsi_use_stoch.get(), self.entry_rsi_use_rsi.get()))
        self.entry_rsi_stoch_up_long_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_rsi_stoch_up_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_stoch_up_long)
        self.entry_rsi_stoch_low_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_stoch_low_long)
        self.entry_rsi_stoch_up_short_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_rsi_stoch_up_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_stoch_up_short)
        self.entry_rsi_stoch_low_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_stoch_low_short)
        self.entry_rsi_level_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_rsi_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_long)
        self.entry_rsi_short_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_rsi_short)

        # PRICE PRESET
        self.entry_price_delta_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_price_delta_short_entry = tk.Entry(self.strategy_left, width=9, textvariable=self.entry_price_delta_short)
        self.entry_price_delta_long_entry = tk.Entry(self.strategy_left, width=8, textvariable=self.entry_price_delta_long)



        # QFL
        # self.entry_qfl_N_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        # self.entry_qfl_N_entry = tk.Entry(self.strategy_left, textvariable=self.entry_qfl_N)
        # self.entry_qfl_M_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        # self.entry_qfl_M_entry = tk.Entry(self.strategy_left, textvariable=self.entry_qfl_M)
        # self.entry_qfl_h_l_percent_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        # self.entry_qfl_h_l_percent_entry = tk.Entry(self.strategy_left, textvariable=self.entry_qfl_h_l_percent)
        #self.entry_qfl_u_o_label = tk.Label(self.strategy_left, width=23, padx=10, pady=2, anchor=tk.W)
        #self.entry_qfl_u_o_list_box = ttk.OptionMenu(self.strategy_left, variable=self.entry_qfl_u_o, style="TMenubutton", command=lambda event: self.entry_qfl_u_o_handle(self.entry_qfl_u_o.get()))

        # MA CROSS
        self.entry_ma1_cross_length_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_ma1_cross_length_entry = tk.Entry(self.strategy_left, textvariable=self.entry_ma1_cross_length)
        self.entry_ma2_cross_length_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_ma2_cross_length_entry = tk.Entry(self.strategy_left, textvariable=self.entry_ma2_cross_length)
        # self.entry_ma_cross_u_o_label = tk.Label(self.strategy_left, width=23, padx=10, pady=2, anchor=tk.W)
        # self.entry_ma_cross_u_o_list_box = ttk.OptionMenu(self.strategy_left, variable=self.entry_ma_cross_u_o, style="TMenubutton", command=lambda event: self.entry_ma_cross_u_o_handle(self.entry_ma_cross_u_o.get()))

        # SMARSI CROSS
        self.entry_smarsi_cross_long_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_smarsi_cross_short_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        self.entry_smarsi_cross_up_long_entry = tk.Entry(self.strategy_left, width=9, textvariable=self.entry_smarsi_cross_up_long)
        self.entry_smarsi_cross_low_long_entry = tk.Entry(self.strategy_left, width=8, textvariable = self.entry_smarsi_cross_low_long)
        self.entry_smarsi_cross_up_short_entry = tk.Entry(self.strategy_left, width=9, textvariable=self.entry_smarsi_cross_up_short)
        self.entry_smarsi_cross_low_short_entry = tk.Entry(self.strategy_left, width=8, textvariable = self.entry_smarsi_cross_low_short)
        # self.entry_smarsi_cross_length_label = tk.Label(self.strategy_left, width=23, padx=10, anchor=tk.W)
        # self.entry_smarsi_cross_length_entry = tk.Entry(self.strategy_left, textvariable = self.entry_smarsi_cross_length)

        # AVR
        self.averaging_conditions_label = tk.Label(self.strategy_center, width=20, padx=7, pady=2, anchor=tk.W, font="Tahoma 8 bold")
        self.averaging_conditions_label.grid(column=0, row=0, sticky="W", pady=2)

        # AVERAGING
        self.avg_use_tf_switching_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_use_tf_switching_label.grid(column=0, row=1, sticky="W", pady=2)
        self.avg_use_tf_switching_yes = tk.Radiobutton(self.strategy_center, text="yes", variable=self.avg_use_tf_switching, value=True, padx=3, pady=2, command=lambda: self.avg_use_tf_switching_handle(self.avg_use_tf_switching.get()))
        self.avg_use_tf_switching_yes.grid(column=1, row=1, sticky="W", padx=5)
        self.avg_use_tf_switching_no = tk.Radiobutton(self.strategy_center, text="no", variable=self.avg_use_tf_switching, value=False, pady=2, command=lambda: self.avg_use_tf_switching_handle(self.avg_use_tf_switching.get()))
        self.avg_use_tf_switching_no.grid(column=2, row=1, sticky="E", padx=5)

        self.timeframe_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
        self.timeframe_entry = tk.Entry(self.strategy_center, textvariable=self.timeframe)
        self.timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="E")

        self.avg_preset_label = tk.Label(self.strategy_center, width=24, padx=6, pady=4, anchor=tk.W)
        self.avg_preset_label.grid(column=0, row=3, sticky="W", pady=0)
        self.avg_preset_list_box = ttk.OptionMenu(self.strategy_center, variable=self.avg_preset, style="TMenubutton", command=lambda event: self.avg_preset_handle(self.avg_preset.get()))
        self.avg_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="E")

        self.avg_cci_cross_use_price_label = tk.Label(self.strategy_center, width=24, padx=6, pady=4, anchor=tk.W)
        self.avg_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=0)
        self.avg_cci_cross_use_price_yes = tk.Radiobutton(self.strategy_center, text="yes", variable=self.avg_cci_cross_use_price, value=True, pady=2, command=lambda: self.avg_cci_cross_use_price_handle(self.avg_cci_cross_use_price.get()))
        self.avg_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=7)
        self.avg_cci_cross_use_price_no = tk.Radiobutton(self.strategy_center, text="no", variable=self.avg_cci_cross_use_price, value=False, pady=2, command=lambda: self.avg_cci_cross_use_price_handle(self.avg_cci_cross_use_price.get()))
        self.avg_cci_cross_use_price_no.grid(column=2, row=4, sticky="E", padx=5)

        # AVG for cci_cross preset
        self.avg_cci_cross_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_cci_cross_long)
        self.avg_cci_cross_short_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_cci_cross_short)

        #self.avg_cci_cross_u_o_label = tk.Label(self.strategy_center, width=23, padx=6, pady=2, anchor=tk.W)
        #self.avg_cci_cross_u_o_list_box = ttk.OptionMenu(self.strategy_center, variable=self.avg_cci_cross_u_o, style="TMenubutton", command=lambda event: self.avg_cci_cross_u_o_handle(self.avg_cci_cross_u_o.get()))



        # CCI
        # STOCH_CCI
        self.avg_use_stoch_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_use_stoch_checkbutton = tk.Checkbutton(self.strategy_center, variable=self.avg_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.avg_use_stoch_or_cci_handle(self.avg_basic_indicator.get(), self.avg_use_stoch.get(), self.avg_use_cci.get()))
        self.avg_use_stoch_status_label = tk.Label(self.strategy_center, anchor=tk.W)
        self.avg_use_cci_checkbutton = tk.Checkbutton(self.strategy_center, variable=self.avg_use_cci, text="cci", onvalue=1, offvalue=0, command=lambda: self.avg_use_stoch_or_cci_handle(self.avg_basic_indicator.get(), self.avg_use_stoch.get(), self.avg_use_cci.get()))
        self.avg_use_cci_status_label = tk.Label(self.strategy_center, anchor=tk.W)
        self.avg_basic_indicator_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_basic_indicator_stoch = tk.Radiobutton(self.strategy_center, text="stoch", variable=self.avg_basic_indicator, value='stoch', pady=2, command=lambda: self.avg_basic_indicator_handle(self.avg_basic_indicator.get(), self.avg_use_stoch.get(), self.avg_use_cci.get()))
        self.avg_basic_indicator_cci = tk.Radiobutton(self.strategy_center, text="cci", variable=self.avg_basic_indicator, value='cci', pady=2, command=lambda: self.avg_basic_indicator_handle(self.avg_basic_indicator.get(), self.avg_use_stoch.get(), self.avg_use_cci.get()))
        self.avg_stoch_up_long_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_stoch_up_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_stoch_up_long)
        self.avg_stoch_low_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_stoch_low_long)
        self.avg_stoch_up_short_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_stoch_up_short_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_stoch_up_short)
        self.avg_stoch_low_short_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_stoch_low_short)
        self.avg_cci_level_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_cci_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_cci_long)
        self.avg_cci_short_entry = tk.Entry(self.strategy_center,width=8, textvariable=self.avg_cci_short)

        # RSI
        # STOCH_RSI
        self.avg_rsi_use_stoch_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_rsi_use_stoch_checkbutton = tk.Checkbutton(self.strategy_center, variable=self.avg_rsi_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.avg_use_stoch_or_rsi_handle(self.avg_rsi_basic_indicator.get(), self.avg_rsi_use_stoch.get(), self.avg_rsi_use_rsi.get()))
        self.avg_rsi_use_stoch_status_label = tk.Label(self.strategy_center, anchor=tk.W)
        self.avg_rsi_use_rsi_checkbutton = tk.Checkbutton(self.strategy_center, variable=self.avg_rsi_use_rsi, text="rsi", onvalue=1, offvalue=0, command=lambda: self.avg_use_stoch_or_rsi_handle(self.avg_rsi_basic_indicator.get(), self.avg_rsi_use_stoch.get(), self.avg_rsi_use_rsi.get()))
        self.avg_rsi_use_rsi_status_label = tk.Label(self.strategy_center, anchor=tk.W)
        self.avg_rsi_basic_indicator_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_rsi_basic_indicator_stoch = tk.Radiobutton(self.strategy_center, text="stoch", variable=self.avg_rsi_basic_indicator, value='stoch', pady=2, command=lambda: self.avg_rsi_basic_indicator_handle(self.avg_rsi_basic_indicator.get(), self.avg_rsi_use_stoch.get(), self.avg_rsi_use_rsi.get()))
        self.avg_rsi_basic_indicator_rsi = tk.Radiobutton(self.strategy_center, text="rsi", variable=self.avg_rsi_basic_indicator, value='rsi', pady=2, command=lambda: self.avg_rsi_basic_indicator_handle(self.avg_rsi_basic_indicator.get(), self.avg_rsi_use_stoch.get(), self.avg_rsi_use_rsi.get()))
        self.avg_rsi_stoch_up_long_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_rsi_stoch_up_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_rsi_stoch_up_long)
        self.avg_rsi_stoch_low_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_rsi_stoch_low_long)
        self.avg_rsi_stoch_up_short_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_rsi_stoch_up_short_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_rsi_stoch_up_short)
        self.avg_rsi_stoch_low_short_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_rsi_stoch_low_short)
        self.avg_rsi_level_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_rsi_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_rsi_long)
        self.avg_rsi_short_entry = tk.Entry(self.strategy_center,width=8, textvariable=self.avg_rsi_short)

        # PRICE PRESET
        self.avg_price_delta_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_price_delta_short_entry = tk.Entry(self.strategy_center, width=9, textvariable=self.avg_price_delta_short)
        self.avg_price_delta_long_entry = tk.Entry(self.strategy_center, width=8, textvariable=self.avg_price_delta_long)


        # QFL
        # self.avg_qfl_N_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        # self.avg_qfl_N_entry = tk.Entry(self.strategy_center, textvariable=self.avg_qfl_N)
        # self.avg_qfl_M_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        # self.avg_qfl_M_entry = tk.Entry(self.strategy_center, textvariable=self.avg_qfl_M)
        # self.avg_qfl_h_l_percent_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        # self.avg_qfl_h_l_percent_entry = tk.Entry(self.strategy_center, textvariable=self.avg_qfl_h_l_percent)
        #self.avg_qfl_u_o_label = tk.Label(self.strategy_center, width=24, padx=6, pady=2, anchor=tk.W)
        #self.avg_qfl_u_o_list_box = ttk.OptionMenu(self.strategy_center, variable=self.avg_qfl_u_o, style="TMenubutton", command=lambda event: self.avg_qfl_u_o_handle(self.avg_qfl_u_o.get()))

        # MA CROSS
        self.avg_ma1_cross_length_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_ma1_cross_length_entry = tk.Entry(self.strategy_center, textvariable=self.avg_ma1_cross_length)
        self.avg_ma2_cross_length_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_ma2_cross_length_entry = tk.Entry(self.strategy_center, textvariable=self.avg_ma2_cross_length)
        # self.avg_ma_cross_u_o_label = tk.Label(self.strategy_center, width=24, padx=6, pady=2, anchor=tk.W)
        # self.avg_ma_cross_u_o_list_box = ttk.OptionMenu(self.strategy_center, variable=self.avg_ma_cross_u_o, style="TMenubutton", command=lambda event: self.avg_ma_cross_u_o_handle(self.avg_ma_cross_u_o.get()))

        # SMARSI CROSS
        self.avg_smarsi_cross_long_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_smarsi_cross_short_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        self.avg_smarsi_cross_up_long_entry = tk.Entry(self.strategy_center, width=9, textvariable=self.avg_smarsi_cross_up_long)
        self.avg_smarsi_cross_low_long_entry = tk.Entry(self.strategy_center, width=8, textvariable = self.avg_smarsi_cross_low_long)
        self.avg_smarsi_cross_up_short_entry = tk.Entry(self.strategy_center, width=9, textvariable=self.avg_smarsi_cross_up_short)
        self.avg_smarsi_cross_low_short_entry = tk.Entry(self.strategy_center, width=8, textvariable = self.avg_smarsi_cross_low_short)
        # self.avg_smarsi_cross_length_label = tk.Label(self.strategy_center, width=24, padx=6, anchor=tk.W)
        # self.avg_smarsi_cross_length_entry = tk.Entry(self.strategy_center, textvariable = self.avg_smarsi_cross_length)


        # EXIT TITLE
        self.exit_conditions_label = tk.Label(self.strategy_right, width=24, pady=2, anchor=tk.W, font="Tahoma 8 bold")
        self.exit_conditions_label.grid(column=0, row=0, columnspan=2, sticky="W")

        # SELECT PROFIT
        self.take_profit_label = tk.Label(self.strategy_right, width=24, pady=2, anchor=tk.W)
        self.take_profit_label.grid(column=0, row=1, sticky="W", pady=3)
        self.take_profit_list_box = ttk.OptionMenu(self.strategy_right, variable=self.take_profit, style="TMenubutton", command=lambda event: self.take_profit_handle(self.take_profit.get()))
        self.take_profit_list_box.grid(column=1, columnspan=3, row=1, sticky="W", padx=5)

        self.exit_timeframe_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_timeframe_entry = tk.Entry(self.strategy_right, textvariable=self.exit_timeframe)

        self.exit_preset_label = tk.Label(self.strategy_right, width=24, pady=2, anchor=tk.W)
        self.exit_preset_list_box = ttk.OptionMenu(self.strategy_right, variable=self.exit_preset, style="TMenubutton", command=lambda event: self.exit_preset_handle(self.exit_preset.get()))

        self.exit_cci_cross_use_price_label = tk.Label(self.strategy_right, width = 24, pady = 2, anchor = tk.W)
        self.exit_cci_cross_use_price_yes = tk.Radiobutton(self.strategy_right, text="yes", variable=self.exit_cci_cross_use_price, value=True, padx=5, pady=2, command=lambda: self.exit_cci_cross_use_price_handle(self.exit_cci_cross_use_price.get()))
        self.exit_cci_cross_use_price_no = tk.Radiobutton(self.strategy_right, text="no", variable=self.exit_cci_cross_use_price, value=False, padx=7, pady=2, command=lambda: self.exit_cci_cross_use_price_handle(self.exit_cci_cross_use_price.get()))

        # EXIT for cci_cross preset
        self.exit_cci_cross_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_cci_cross_long)
        self.exit_cci_cross_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_cci_cross_short)

        #self.exit_cci_cross_u_o_label = tk.Label(self.strategy_right, width=23, pady=2, anchor=tk.W)
        #self.exit_cci_cross_u_o_list_box = ttk.OptionMenu(self.strategy_right, variable=self.exit_cci_cross_u_o, style="TMenubutton", command=lambda event: self.exit_cci_cross_u_o_handle(self.exit_cci_cross_u_o.get()))


        #CCI
        #STOCH_CCI
        self.exit_use_stoch_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_use_stoch_checkbutton = tk.Checkbutton(self.strategy_right, variable=self.exit_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.exit_use_stoch_or_cci_handle(self.exit_basic_indicator.get(), self.exit_use_stoch.get(), self.exit_use_cci.get()))
        self.exit_use_stoch_status_label = tk.Label(self.strategy_right, anchor=tk.W)
        self.exit_use_cci_checkbutton = tk.Checkbutton(self.strategy_right, variable=self.exit_use_cci, text="cci", onvalue=1, offvalue=0, command=lambda: self.exit_use_stoch_or_cci_handle(self.exit_basic_indicator.get(), self.exit_use_stoch.get(), self.exit_use_cci.get()))
        self.exit_use_cci_status_label = tk.Label(self.strategy_right, anchor=tk.W)
        self.exit_basic_indicator_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_basic_indicator_stoch = tk.Radiobutton(self.strategy_right, text="stoch", variable=self.exit_basic_indicator, value='stoch', pady=2, command=lambda: self.exit_basic_indicator_handle(self.exit_basic_indicator.get(), self.exit_use_stoch.get(), self.exit_use_cci.get()))
        self.exit_basic_indicator_cci = tk.Radiobutton(self.strategy_right, text="cci", variable=self.exit_basic_indicator, value='cci', pady=2, command=lambda: self.exit_basic_indicator_handle(self.exit_basic_indicator.get(), self.exit_use_stoch.get(), self.exit_use_cci.get()))
        self.exit_stoch_up_long_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_stoch_up_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_stoch_up_long)
        self.exit_stoch_low_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_stoch_low_long)
        self.exit_stoch_up_short_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_stoch_up_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_stoch_up_short)
        self.exit_stoch_low_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_stoch_low_short)
        self.exit_cci_level_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_cci_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_cci_long)
        self.exit_cci_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_cci_short)

        #RSI
        #STOCH_RSI
        self.exit_rsi_use_stoch_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_rsi_use_stoch_checkbutton = tk.Checkbutton(self.strategy_right, variable=self.exit_rsi_use_stoch, text="stoch", onvalue=1, offvalue=0, command=lambda: self.exit_use_stoch_or_rsi_handle(self.exit_rsi_basic_indicator.get(), self.exit_rsi_use_stoch.get(), self.exit_rsi_use_rsi.get()))
        self.exit_rsi_use_stoch_status_label = tk.Label(self.strategy_right, anchor=tk.W)
        self.exit_rsi_use_rsi_checkbutton = tk.Checkbutton(self.strategy_right, variable=self.exit_rsi_use_rsi, text="rsi", onvalue=1, offvalue=0, command=lambda: self.exit_use_stoch_or_rsi_handle(self.exit_rsi_basic_indicator.get(), self.exit_rsi_use_stoch.get(), self.exit_rsi_use_rsi.get()))
        self.exit_rsi_use_rsi_status_label = tk.Label(self.strategy_right, anchor=tk.W)
        self.exit_rsi_basic_indicator_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_rsi_basic_indicator_stoch = tk.Radiobutton(self.strategy_right, text="stoch", variable=self.exit_rsi_basic_indicator, value='stoch', pady=2, command=lambda: self.exit_rsi_basic_indicator_handle(self.exit_rsi_basic_indicator.get(), self.exit_rsi_use_stoch.get(), self.exit_rsi_use_rsi.get()))
        self.exit_rsi_basic_indicator_rsi = tk.Radiobutton(self.strategy_right, text="rsi", variable=self.exit_rsi_basic_indicator, value='rsi', pady=2, command=lambda: self.exit_rsi_basic_indicator_handle(self.exit_rsi_basic_indicator.get(), self.exit_rsi_use_stoch.get(), self.exit_rsi_use_rsi.get()))
        self.exit_rsi_stoch_up_long_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_rsi_stoch_up_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_stoch_up_long)
        self.exit_rsi_stoch_low_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_stoch_low_long)
        self.exit_rsi_stoch_up_short_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_rsi_stoch_up_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_stoch_up_short)
        self.exit_rsi_stoch_low_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_stoch_low_short)
        self.exit_rsi_level_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_rsi_long_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_long)
        self.exit_rsi_short_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_rsi_short)



        # PROFIT EXIT Profit simple DSO off
        # Squeeze profit
        self.squeeze_profit_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.squeeze_profit_label.grid(column=0, row=8, sticky="W", pady=3)
        self.squeeze_profit_entry = tk.Entry(self.strategy_right, textvariable=self.squeeze_profit)
        self.squeeze_profit_entry.grid(column=1, columnspan=2, row=8, sticky="W", padx=5)

        self.exit_profit_level_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        #self.exit_profit_level_label.grid(column=0, row=9, sticky="W", pady=2)
        self.exit_profit_level_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_profit_level)
        self.exit_stop_loss_level_entry = tk.Entry(self.strategy_right, width=8, textvariable=self.exit_stop_loss_level)


        #self.exit_profit_level_label.config(text=LANGUAGES[self.lang.get()]["exit_profit_level_label"])



        # TRAILING EXIT Trailing
        self.trailing_stop_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.trailing_stop_entry = tk.Entry(self.strategy_right, textvariable=self.trailing_stop)
        self.limit_stop_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.limit_stop_entry = tk.Entry(self.strategy_right, textvariable=self.limit_stop)

        # QFL
        # self.exit_qfl_N_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        # self.exit_qfl_N_entry = tk.Entry(self.strategy_right, textvariable=self.exit_qfl_N)
        # self.exit_qfl_M_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        # self.exit_qfl_M_entry = tk.Entry(self.strategy_right, textvariable=self.exit_qfl_M)
        # self.exit_qfl_h_l_percent_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        # self.exit_qfl_h_l_percent_entry = tk.Entry(self.strategy_right, textvariable=self.exit_qfl_h_l_percent)
        #self.exit_qfl_u_o_label = tk.Label(self.strategy_right, width=24, pady=2, anchor=tk.W)
        #self.exit_qfl_u_o_list_box = ttk.OptionMenu(self.strategy_right, variable=self.exit_qfl_u_o, style="TMenubutton", command=lambda event: self.exit_qfl_u_o_handle(self.exit_qfl_u_o.get()))

        # MA CROSS
        self.exit_ma1_cross_length_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_ma1_cross_length_entry = tk.Entry(self.strategy_right, textvariable=self.exit_ma1_cross_length)
        self.exit_ma2_cross_length_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_ma2_cross_length_entry = tk.Entry(self.strategy_right, textvariable=self.exit_ma2_cross_length)
        # self.exit_ma_cross_u_o_label = tk.Label(self.strategy_right, width=24, pady=2, anchor=tk.W)
        # self.exit_ma_cross_u_o_list_box = ttk.OptionMenu(self.strategy_right, variable=self.exit_ma_cross_u_o, style="TMenubutton", command=lambda event: self.exit_ma_cross_u_o_handle(self.exit_ma_cross_u_o.get()))

        # SMARSI CROSS
        self.exit_smarsi_cross_long_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_smarsi_cross_short_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        self.exit_smarsi_cross_up_long_entry = tk.Entry(self.strategy_right, width=9, textvariable=self.exit_smarsi_cross_up_long)
        self.exit_smarsi_cross_low_long_entry = tk.Entry(self.strategy_right, width=8, textvariable = self.exit_smarsi_cross_low_long)
        self.exit_smarsi_cross_up_short_entry = tk.Entry(self.strategy_right, width=9, textvariable=self.exit_smarsi_cross_up_short)
        self.exit_smarsi_cross_low_short_entry = tk.Entry(self.strategy_right, width=8, textvariable = self.exit_smarsi_cross_low_short)
        # self.exit_smarsi_cross_length_label = tk.Label(self.strategy_right, width=24, anchor=tk.W)
        # self.exit_smarsi_cross_length_entry = tk.Entry(self.strategy_right, textvariable = self.exit_smarsi_cross_length)


        # Indicators_fine_tuning TITLE
        self.indicators_fine_tuning_label = tk.Label(self.advanced_left, width=23, padx=10, pady=5, anchor=tk.W, font="Tahoma 8 bold")
        self.indicators_fine_tuning_label.grid(column=0, columnspan=3, row=0, sticky="W")

        self.global_timeframe_label = tk.Label(self.advanced_left, width=23, padx=10, pady=4, anchor=tk.W)
        self.global_timeframe_label.grid(column=0, row=1, sticky="W", pady=3)
        self.global_timeframe_entry = tk.Entry(self.advanced_left, textvariable=self.global_timeframe)
        self.global_timeframe_entry.grid(column=1, columnspan=3, row=1, sticky="W", padx=5)

        self.use_stoch_rsi_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        self.use_stoch_rsi_label.grid(column=0, row=2, sticky="W")
        self.use_stoch_rsi_yes = tk.Radiobutton(self.advanced_left, text="yes", variable=self.use_stoch_rsi, value=True, padx=5, pady=2, command=lambda: self.use_stoch_rsi_handle(self.use_stoch_rsi.get()))
        self.use_stoch_rsi_yes.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
        self.use_stoch_rsi_no = tk.Radiobutton(self.advanced_left, text="no", variable=self.use_stoch_rsi, value=False, padx=3, pady=2, command=lambda: self.use_stoch_rsi_handle(self.use_stoch_rsi.get()))
        self.use_stoch_rsi_no.grid(column=2, columnspan=2, row=2, sticky="E", padx=4)

        self.use_global_stoch_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        self.use_global_stoch_label.grid(column=0, row=3, sticky="W")
        self.use_global_stoch_yes = tk.Radiobutton(self.advanced_left, text="yes", variable=self.use_global_stoch, value=True, padx=5, pady=2, command=lambda: self.use_global_stoch_handle(self.use_global_stoch.get()))
        self.use_global_stoch_yes.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)
        self.use_global_stoch_no = tk.Radiobutton(self.advanced_left, text="no", variable=self.use_global_stoch, value=False, padx=3, pady=2, command=lambda: self.use_global_stoch_handle(self.use_global_stoch.get()))
        self.use_global_stoch_no.grid(column=2, columnspan=2, row=3, sticky="E", padx=4)

        self.global_stoch_short_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        self.global_stoch_short_label.grid(column=0, row=4, sticky="W")
        self.global_stoch_up_short_entry = tk.Entry(self.advanced_left, width=9, textvariable=self.global_stoch_up_short)
        self.global_stoch_up_short_entry.grid(column=1, columnspan=2, row=4, sticky="W", pady=3, padx=5)
        self.global_stoch_low_short_entry = tk.Entry(self.advanced_left, width=8, textvariable=self.global_stoch_low_short)
        self.global_stoch_low_short_entry.grid(column=2, columnspan=2, row=4, sticky="E")

        self.global_stoch_long_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        self.global_stoch_long_label.grid(column=0, row=5, sticky="W")
        self.global_stoch_up_long_entry = tk.Entry(self.advanced_left, width=9, textvariable=self.global_stoch_up_long)
        self.global_stoch_up_long_entry.grid(column=1, columnspan=2, row=5, sticky="W", pady=3, padx=5)
        self.global_stoch_low_long_entry = tk.Entry(self.advanced_left, width=8, textvariable=self.global_stoch_low_long)
        self.global_stoch_low_long_entry.grid(column=2, columnspan=2, row=5, sticky="E")

        self.empty_label_1 = tk.Label(self.advanced_left, width=24, padx=10, pady=20, anchor=tk.W)
        self.empty_label_1.grid(column=0, row=6, columnspan=2, sticky="W")
        self.use_dynamic_so_label = tk.Label(self.advanced_left, width=24, padx=5, anchor=tk.W)


        # self.stoch_fastk_period_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.stoch_fastk_period_label.grid(column=0, row=3, sticky="W", pady=3)
        # self.stoch_fastk_period_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.stoch_fastk_period)
        # self.stoch_fastk_period_entry.grid(column=1, row=3, sticky="W", padx=5)
        # self.stoch_slowk_period_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.stoch_slowk_period)
        # self.stoch_slowk_period_entry.grid(column=2, row=3, sticky="W", padx=5)
        # self.stoch_slowd_period_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.stoch_slowd_period)
        # self.stoch_slowd_period_entry.grid(column=3, row=3, sticky="W", padx=5)
        #
        # self.cci_length_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.cci_length_label.grid(column=0, row=4, sticky="W", pady=2)
        # self.cci_length_entry = tk.Entry(self.advanced_left, textvariable=self.cci_length)
        # self.cci_length_entry.grid(column=1, columnspan=3, row=4, sticky="W", padx=5)
        #
        # self.ema200_and_delta_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.ema200_and_delta_label.grid(column=0, row=5, sticky="W", pady=2)
        # self.ema200_entry = tk.Entry(self.advanced_left, width=9, textvariable=self.ema200)
        # self.ema200_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
        # self.ema200_delta_entry = tk.Entry(self.advanced_left, width=8, textvariable=self.ema200_delta)
        # self.ema200_delta_entry.grid(column=2, columnspan=2, row=5, sticky="E", padx=5)
        #
        # self.macd_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.macd_label.grid(column=0, row=6, sticky="W", pady=2)
        # self.macd_f_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.macd_f)
        # self.macd_f_entry.grid(column=1, row=6, sticky="W", padx=5)
        # self.macd_s_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.macd_s)
        # self.macd_s_entry.grid(column=2, row=6, sticky="W", padx=5)
        # self.macd_signal_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.macd_signal)
        # self.macd_signal_entry.grid(column=3, row=6, sticky="W", padx=5)
        #
        # self.rsi_atr_efi_length_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.rsi_atr_efi_length_label.grid(column=0, row=7, sticky="W", pady=2)
        # self.rsi_length_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.rsi_length)
        # self.rsi_length_entry.grid(column=1, row=7, sticky="W", padx=5)
        # self.atr_length_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.atr_length)
        # self.atr_length_entry.grid(column=2, row=7, sticky="W", padx=5)
        # self.efi_length_entry = tk.Entry(self.advanced_left, width=5, textvariable=self.efi_length)
        # self.efi_length_entry.grid(column=3, row=7, sticky="W", padx=5)

        # self.bb_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.bb_label.grid(column=0, row=8, sticky="W", pady=2)
        # self.bb_period_entry = tk.Entry(self.advanced_left, width=9, textvariable=self.bb_period)
        # self.bb_period_entry.grid(column=1, columnspan=2, row=8, sticky="W", padx=5)
        # self.bb_dev_entry = tk.Entry(self.advanced_left, width=8, textvariable=self.bb_dev)
        # self.bb_dev_entry.grid(column=2, columnspan=2, row=8, sticky="E", padx=5)

        # self.supertrend_label = tk.Label(self.advanced_left, width=23, padx=10, anchor=tk.W)
        # self.supertrend_label.grid(column=0, row=8, sticky="W", pady=3)
        # self.supertrend_period_entry = tk.Entry(self.advanced_left, width=9, textvariable=self.supertrend_period)
        # self.supertrend_period_entry.grid(column=1, columnspan=2, row=8, sticky="W", padx=5)
        # self.supertrend_multiplier_entry = tk.Entry(self.advanced_left, width=8, textvariable=self.supertrend_multiplier)
        # self.supertrend_multiplier_entry.grid(column=2, columnspan=2, row=8, sticky="W", padx=5)

        # TIMEFRAME SWITCH TITLE
        self.timeframe_switching_label = tk.Label(self.advanced_center, width=26,  pady=5, anchor=tk.W, font="Tahoma 8 bold")

        self.ema_global_switch_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.ema_global_switch_yes = tk.Radiobutton(self.advanced_center, text="yes", variable=self.ema_global_switch, value=True, pady=1, command=lambda: self.ema_global_switch_handle(self.ema_global_switch.get()))
        self.ema_global_switch_no = tk.Radiobutton(self.advanced_center, text="no", variable=self.ema_global_switch, value=False, pady=1, command=lambda: self.ema_global_switch_handle(self.ema_global_switch.get()))

        self.orders_switch_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.orders_switch_yes = tk.Radiobutton(self.advanced_center, text="yes", variable=self.orders_switch, value=True, pady=1, command=lambda: self.orders_switch_handle(self.orders_switch.get()))
        self.orders_switch_no = tk.Radiobutton(self.advanced_center, text="no", variable=self.orders_switch, value=False, pady=1, command=lambda: self.orders_switch_handle(self.orders_switch.get()))

        self.orders_count_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.orders_count_entry = tk.Entry(self.advanced_center, textvariable=self.orders_count)

        self.last_candle_switch_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.last_candle_switch_yes = tk.Radiobutton(self.advanced_center, text="yes", variable=self.last_candle_switch, value=True, pady=1, command=lambda: self.last_candle_switch_handle(self.last_candle_switch.get()))
        self.last_candle_switch_no = tk.Radiobutton(self.advanced_center, text="no", variable=self.last_candle_switch, value=False, pady=1, command=lambda: self.last_candle_switch_handle(self.last_candle_switch.get()))

        self.last_candle_count_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.last_candle_count_entry = tk.Entry(self.advanced_center, width=9, textvariable=self.last_candle_count)
        self.last_candle_orders_entry = tk.Entry(self.advanced_center, width=8, textvariable=self.last_candle_orders)

        self.stoch_adjustment_label = tk.Label(self.advanced_center, width=24, anchor=tk.W)
        self.stoch_adjustment_entry = tk.Entry(self.advanced_center, textvariable=self.stoch_adjustment)

        self.empty_label_4 = tk.Label(self.advanced_center, width=40, padx=9, pady=0, anchor=tk.W)

        # Miscellaneous
        self.miscellaneous_label = tk.Label(self.advanced_right, width=26,  pady=5, anchor=tk.W, font="Tahoma 8 bold")
        self.miscellaneous_label.grid(column=0, columnspan=2, row=0, sticky="W")

        # self.immediate_so_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        # self.immediate_so_label.grid(column=0, row=1, sticky="W", pady=4)
        # self.immediate_so_yes = tk.Radiobutton(self.advanced_right, text="yes", variable=self.immediate_so, value=True, pady=1, command=lambda: self.immediate_so_handle(self.immediate_so.get()))
        # self.immediate_so_yes.grid(column=1, row=1, sticky="W", padx=5)
        # self.immediate_so_no = tk.Radiobutton(self.advanced_right, text="no", variable=self.immediate_so, value=False, pady=1, command=lambda: self.immediate_so_handle(self.immediate_so.get()))
        # self.immediate_so_no.grid(column=2, row=1, sticky="E", padx=8)

        self.back_profit_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        self.back_profit_label .grid(column=0, row=2, sticky="W", pady=2)
        self.back_profit_entry = tk.Entry(self.advanced_right, textvariable=self.back_profit)
        self.back_profit_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=2)

        self.so_safety_price_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        self.so_safety_price_label.grid(column=0, row=3, sticky="W", pady=2)
        self.so_safety_price_entry = tk.Entry(self.advanced_right, textvariable=self.so_safety_price)
        self.so_safety_price_entry.grid(column=1, columnspan=2, row=3, sticky="W", padx=2)

        self.emergency_averaging_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        self.emergency_averaging_label.grid(column=0, row=4, sticky="W", pady=2)
        self.emergency_averaging_entry = tk.Entry(self.advanced_right, textvariable=self.emergency_averaging)
        self.emergency_averaging_entry.grid(column=1, columnspan=2, row=4, sticky="W", padx=2)

        self.use_margin_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        self.use_margin_label.grid(column=0, row=5, sticky="W", pady=2)
        self.use_margin_yes = tk.Radiobutton(self.advanced_right, text="yes", variable=self.use_margin, value=True, pady=4, command=lambda: self.use_margin_handle(self.use_margin.get()))
        self.use_margin_yes.grid(column=1, row=5, sticky="W", padx=5)
        self.use_margin_no = tk.Radiobutton(self.advanced_right, text="no", variable=self.use_margin, value=False, pady=4, command=lambda: self.use_margin_handle(self.use_margin.get()))
        self.use_margin_no.grid(column=2, row=5, sticky="E", padx=8)

        self.margin_top_and_bottom_label = tk.Label(self.advanced_right, width=25, anchor=tk.W)
        self.margin_top_and_bottom_label.grid(column=0, row=6, sticky="W", pady=2)
        self.margin_top_entry = tk.Entry(self.advanced_right, width=9, textvariable=self.margin_top)
        self.margin_top_entry.grid(column=1, row=6, sticky="W", padx=2)
        self.margin_bottom_entry = tk.Entry(self.advanced_right, width=8, textvariable=self.margin_bottom)
        self.margin_bottom_entry.grid(column=2, row=6, sticky="E", padx=2)

        # Logging widget
        # self.empty_label_1 = tk.Label(self.advanced_left, width=0, anchor=tk.W)
        # self.empty_label_1.grid(column=0, row=30, sticky="W")
        self.logging_widget = tkst.ScrolledText(self.row_31, width=125, height=41)
        #self.logging_widget.grid(row=31)

    def margin_mode_handle(self, margin_mode):
        self.config.set_value("bot", "margin_mode", margin_mode)
        self.config.save()

    def entry_by_indicators_handle(self, entry_by_indicators):
        self.config.set_value("entry", "entry_by_indicators", entry_by_indicators)
        self.config.save()
        if entry_by_indicators == False:
            #= state = DISABLED
            self.entry_timeframe_label.grid_forget()
            self.entry_timeframe_entry.grid_forget()
            self.entry_preset_label.grid_forget()
            self.entry_preset_list_box.grid_forget()

            self.entry_use_stoch_label.grid_forget()
            self.entry_use_stoch_checkbutton.grid_forget()
            self.entry_use_cci_checkbutton.grid_forget()
            self.entry_use_stoch_status_label.grid_forget()
            self.entry_use_cci_status_label.grid_forget()
            self.entry_basic_indicator_label.grid_forget()
            self.entry_basic_indicator_stoch.grid_forget()
            self.entry_basic_indicator_cci.grid_forget()
            self.entry_stoch_up_long_label.grid_forget()
            self.entry_stoch_up_long_entry.grid_forget()
            self.entry_stoch_low_long_entry.grid_forget()
            self.entry_stoch_up_short_label.grid_forget()
            self.entry_stoch_up_short_entry.grid_forget()
            self.entry_stoch_low_short_entry.grid_forget()
            self.entry_cci_level_label.grid_forget()
            self.entry_cci_long_entry.grid_forget()
            self.entry_cci_short_entry.grid_forget()

            self.entry_rsi_use_stoch_label.grid_forget()
            self.entry_rsi_use_stoch_checkbutton.grid_forget()
            self.entry_rsi_use_rsi_checkbutton.grid_forget()
            self.entry_rsi_use_stoch_status_label.grid_forget()
            self.entry_rsi_use_rsi_status_label.grid_forget()
            self.entry_rsi_basic_indicator_label.grid_forget()
            self.entry_rsi_basic_indicator_stoch.grid_forget()
            self.entry_rsi_basic_indicator_rsi.grid_forget()
            self.entry_rsi_stoch_up_long_label.grid_forget()
            self.entry_rsi_stoch_up_long_entry.grid_forget()
            self.entry_rsi_stoch_low_long_entry.grid_forget()
            self.entry_rsi_stoch_up_short_label.grid_forget()
            self.entry_rsi_stoch_up_short_entry.grid_forget()
            self.entry_rsi_stoch_low_short_entry.grid_forget()
            self.entry_rsi_level_label.grid_forget()
            self.entry_rsi_long_entry.grid_forget()
            self.entry_rsi_short_entry.grid_forget()

            self.entry_cci_cross_long_entry.grid_forget()
            self.entry_cci_cross_short_entry.grid_forget()
            self.entry_cci_cross_use_price_label.grid_forget()
            self.entry_cci_cross_use_price_yes.grid_forget()
            self.entry_cci_cross_use_price_no.grid_forget()
            #self.entry_cci_cross_u_o_label.grid_forget()
            #self.entry_cci_cross_u_o_list_box.grid_forget()
            self.entry_ma1_cross_length_label.grid_forget()
            self.entry_ma1_cross_length_entry.grid_forget()
            self.entry_ma2_cross_length_label.grid_forget()
            self.entry_ma2_cross_length_entry.grid_forget()
            # self.entry_ma_cross_u_o_label.grid_forget()
            # self.entry_ma_cross_u_o_list_box.grid_forget()
            self.entry_smarsi_cross_long_label.grid_forget()
            self.entry_smarsi_cross_short_label.grid_forget()
            self.entry_smarsi_cross_up_long_entry.grid_forget()
            self.entry_smarsi_cross_low_long_entry.grid_forget()
            self.entry_smarsi_cross_up_short_entry.grid_forget()
            self.entry_smarsi_cross_low_short_entry.grid_forget()

            self.entry_price_delta_label.grid_forget()
            self.entry_price_delta_short_entry.grid_forget()
            self.entry_price_delta_long_entry.grid_forget()
            # self.entry_smarsi_cross_length_label.grid_forget()
            # self.entry_smarsi_cross_length_entry.grid_forget()

            # self.entry_qfl_N_label.grid_forget()
            # self.entry_qfl_N_entry.grid_forget()
            # self.entry_qfl_M_label.grid_forget()
            # self.entry_qfl_M_entry.grid_forget()
            # self.entry_qfl_h_l_percent_label.grid_forget()
            # self.entry_qfl_h_l_percent_entry.grid_forget()
            #elf.entry_qfl_u_o_label.grid_forget()
            #self.entry_qfl_u_o_list_box.grid_forget()
            # self.entry_use_global_stoch_label.grid_forget()
            # self.entry_use_global_stoch_yes.grid_forget()
            # self.entry_use_global_stoch_no.grid_forget()
            # self.entry_global_stoch_level_label.grid_forget()
            # self.entry_global_stoch_up_level_entry.grid_forget()
            # self.entry_global_stoch_low_level_entry.grid_forget()
            self.empty_label_2.grid(column=0, row=2, padx=0)
            self.empty_label_3.grid(column=1, columnspan=2, row=2, padx=0)
        else:
            self.empty_label_2.grid_forget()
            self.empty_label_3.grid_forget()
            self.entry_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
            self.entry_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
            self.entry_preset_label.grid(column=0, row=3, sticky="W", pady=2)
            self.entry_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

            # self.entry_use_global_stoch_label.grid(column=0, row=8, sticky="W", pady=2)
            # self.entry_use_global_stoch_yes.grid(column=1, row=8, sticky="W", padx=5)
            # self.entry_use_global_stoch_no.grid(column=2, row=8, sticky="W")
            # self.entry_global_stoch_level_label.grid(column=0, row=9, sticky="W", pady=2)
            # self.entry_global_stoch_up_level_entry.grid(column=1, row=9, sticky="W", padx=5)
            # self.entry_global_stoch_low_level_entry.grid(column=2, row=9, sticky="W", padx=2)
            self.entry_preset_handle(self.entry_preset.get())


    def entry_cci_cross_use_price_handle(self, entry_cci_cross_use_price):
        self.config.set_value("entry_preset_cci_cross", "use_price", entry_cci_cross_use_price)
        self.config.save()
        #self.entry_cci_cross_u_o_label.grid_forget()
        #self.entry_cci_cross_u_o_list_box.grid_forget()
        # if entry_cci_cross_use_price == True:
        #     self.entry_cci_cross_u_o_label.grid_forget()
        #     self.entry_cci_cross_u_o_list_box.grid_forget()
        # if entry_cci_cross_use_price == False:
        #     self.entry_cci_cross_u_o_label.grid(column=0, row=6, sticky="W", pady=2)
        #     self.entry_cci_cross_u_o_list_box.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)

    def avg_cci_cross_use_price_handle(self, avg_cci_cross_use_price):
        self.config.set_value("avg_preset_stoch_cci", "use_price", avg_cci_cross_use_price)
        self.config.save()
        # self.avg_cci_cross_u_o_label.grid_forget()
        # self.avg_cci_cross_u_o_list_box.grid_forget()
        # if avg_cci_cross_use_price == True:
        #     self.avg_cci_cross_u_o_label.grid_forget()
        #     self.avg_cci_cross_u_o_list_box.grid_forget()
        # if avg_cci_cross_use_price == False:
        #     self.avg_cci_cross_u_o_label.grid(column=0, row=6, sticky="W", pady=2)
        #     self.avg_cci_cross_u_o_list_box.grid(column=1, columnspan=2, row=6, sticky="E")

    def exit_cci_cross_use_price_handle(self, exit_cci_cross_use_price):
        self.config.set_value("exit_preset_cci_cross", "use_price", exit_cci_cross_use_price)
        self.config.save()
        # self.exit_cci_cross_u_o_label.grid_forget()
        # self.exit_cci_cross_u_o_list_box.grid_forget()
        # if exit_cci_cross_use_price == True:
        #     self.exit_cci_cross_u_o_label.grid_forget()
        #     self.exit_cci_cross_u_o_list_box.grid_forget()
        # if exit_cci_cross_use_price == False:
        #     self.exit_cci_cross_u_o_label.grid(column=0, row=6, sticky="W", pady=2)
        #     self.exit_cci_cross_u_o_list_box.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)

    # def entry_cci_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("entry_preset_cci_cross", "cross_method", cross_method)
    #     self.config.save()

    # def avg_cci_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("avg_preset_cci_cross", "cross_method", cross_method)
    #     self.config.save()
    #
    # def exit_cci_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("exit_preset_cci_cross", "cross_method", cross_method)
    #     self.config.save()

    # def entry_ma_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("entry_preset_ma_cross", "cross_method", cross_method)
    #     self.config.save()
    #
    # def avg_ma_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("avg_preset_ma_cross", "cross_method", cross_method)
    #     self.config.save()
    #
    # def exit_ma_cross_u_o_handle(self, cross_method):
    #     self.config.set_value("exit_preset_ma_cross", "cross_method", cross_method)
    #     self.config.save()

    # def entry_qfl_u_o_handle(self, cross_method):
    #     self.config.set_value("entry_preset_midas", "cross_method", cross_method)
    #     self.config.save()
    #
    # def avg_qfl_u_o_handle(self, cross_method):
    #     self.config.set_value("avg_preset_midas", "cross_method", cross_method)
    #     self.config.save()
    #
    # def exit_qfl_u_o_handle(self, cross_method):
    #     self.config.set_value("exit_preset_midas", "cross_method", cross_method)
    #     self.config.save()


    def select_language_handle(self, lang):
        if lang == "ru":
            self.lang.set("ru")
        else:
            self.lang.set("en")

        self.config.set_value("bot", "language", lang)
        self.config.save()

    def bottype_handle(self, bottype):
        self.config.set_value("bot", "bottype", bottype)
        self.config.save()

    # def one_or_more_handle(self, one_or_more):
    #     self.config.set_value("bot", "one_or_more", one_or_more)
    #     self.config.save()

    # def log_distribution_handle(self, log_distribution):
    #     self.config.set_value("bot", "log_distribution", log_distribution)
    #     self.config.save()

    def cancel_on_trend_handle(self, cancel_on_trend):
        self.config.set_value("bot", "cancel_on_trend", cancel_on_trend)
        self.config.save()

    def grow_first_handle(self, grow_first):
        self.config.set_value("bot", "grow_first", grow_first)
        self.config.save()

    def use_global_stoch_handle(self, use_global_stoch):
        self.config.set_value("indicators_tuning", "use_global_stoch", use_global_stoch)
        self.config.save()

    def avg_use_tf_switching_handle(self, avg_use_tf_switching):
        self.config.set_value("timeframe_switching", "timeframe_switching", avg_use_tf_switching)
        self.config.save()
        # TIMEFRAME SWITCH TITLE
        if avg_use_tf_switching == False:
            self.timeframe_switching_label.grid_forget()
            self.ema_global_switch_label.grid_forget()
            self.ema_global_switch_yes.grid_forget()
            self.ema_global_switch_no.grid_forget()
            self.orders_switch_label.grid_forget()
            self.orders_switch_yes.grid_forget()
            self.orders_switch_no.grid_forget()

            self.orders_count_label.grid_forget()
            self.orders_count_entry.grid_forget()

            self.last_candle_switch_label.grid_forget()
            self.last_candle_switch_yes.grid_forget()
            self.last_candle_switch_no.grid_forget()

            self.last_candle_count_label.grid_forget()
            self.last_candle_count_entry.grid_forget()
            self.last_candle_orders_entry.grid_forget()

            self.stoch_adjustment_label.grid_forget()
            self.stoch_adjustment_entry.grid_forget()
            self.empty_label_4.grid(column=0, columnspan=2, row=0, padx=0)

        else:
            self.timeframe_switching_label.grid_forget()
            self.ema_global_switch_label.grid_forget()
            self.ema_global_switch_yes.grid_forget()
            self.ema_global_switch_no.grid_forget()
            self.orders_switch_label.grid_forget()
            self.orders_switch_yes.grid_forget()
            self.orders_switch_no.grid_forget()

            self.orders_count_label.grid_forget()
            self.orders_count_entry.grid_forget()

            self.last_candle_switch_label.grid_forget()
            self.last_candle_switch_yes.grid_forget()
            self.last_candle_switch_no.grid_forget()

            self.last_candle_count_label.grid_forget()
            self.last_candle_count_entry.grid_forget()
            self.last_candle_orders_entry.grid_forget()

            self.stoch_adjustment_label.grid_forget()
            self.stoch_adjustment_entry.grid_forget()
            self.empty_label_4.grid_forget()

            self.timeframe_switching_label.grid(column=0, columnspan=4, row=0, sticky="W")
            self.ema_global_switch_label.grid(column=0, row=1, sticky="W", pady=4)
            self.ema_global_switch_yes.grid(column=1, row=1, sticky="W", padx=5)
            self.ema_global_switch_no.grid(column=2, row=1, sticky="E", padx=5)
            self.orders_switch_label.grid(column=0, row=2, sticky="W", pady=4)
            self.orders_switch_yes.grid(column=1, row=2, sticky="W", padx=5)
            self.orders_switch_no.grid(column=2, row=2, sticky="E", padx=5)

            self.orders_count_label.grid(column=0, row=3, sticky="W", pady=2)
            self.orders_count_entry.grid(column=1, columnspan=3, row=3, sticky="W", padx=2)

            self.last_candle_switch_label.grid(column=0, row=4, sticky="W", pady=4)
            self.last_candle_switch_yes.grid(column=1, row=4, sticky="W", padx=5)
            self.last_candle_switch_no.grid(column=2, row=4, sticky="E", padx=5)

            self.last_candle_count_label.grid(column=0, row=5, sticky="W", pady=2)
            self.last_candle_count_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=2)
            self.last_candle_orders_entry.grid(column=2, columnspan=2, row=5, sticky="E", padx=2)

            self.stoch_adjustment_label.grid(column=0, row=6, sticky="W", pady=2)
            self.stoch_adjustment_entry.grid(column=1, columnspan=3, row=6, sticky="W", padx=2)


    def use_stoch_rsi_handle(self, use_stoch_rsi):
        self.config.set_value("indicators_tuning", "use_stoch_rsi", use_stoch_rsi)
        self.config.save()

    def ema_global_switch_handle(self, ema_global_switch):
        self.config.set_value("timeframe_switching", "ema_global_switch", ema_global_switch)
        self.config.save()

    def orders_switch_handle(self, orders_switch):
        self.config.set_value("timeframe_switching", "orders_switch", orders_switch)
        self.config.save()

    def last_candle_switch_handle(self, last_candle_switch):
        self.config.set_value("timeframe_switching", "last_candle_switch", last_candle_switch)
        self.config.save()

    # def immediate_so_handle(self, immediate_so):
    #     self.config.set_value("averaging", "immediate_so", immediate_so)
    #     self.config.save()

    def use_margin_handle(self, use_margin):
        self.config.set_value("bot", "use_margin", use_margin)
        self.config.save()

    def entry_use_stoch_or_cci_handle(self, entry_basic_indicator, entry_use_stoch, entry_use_cci):
        lang = self.lang.get()
        if entry_use_stoch == True and entry_use_cci == True:
            if entry_basic_indicator == "stoch" or entry_basic_indicator == "cci":
                self.config.set_value("entry_preset_stoch_cci", "use_stoch", entry_use_stoch)
                self.config.set_value("entry_preset_stoch_cci", "use_cci", entry_use_cci)
                self.config.set_value("entry_preset_stoch_cci", "basic_indicator", entry_basic_indicator)
                self.config.save()
        if entry_use_stoch == False and entry_use_cci == True:
            if entry_basic_indicator == "stoch":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_cci", "use_stoch", entry_use_stoch)
                self.config.set_value("entry_preset_stoch_cci", "use_cci", entry_use_cci)
                self.config.set_value("entry_preset_stoch_cci", "basic_indicator", entry_basic_indicator)
                self.config.save()
        if entry_use_stoch == True and entry_use_cci == False:
            if entry_basic_indicator == "cci":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_cci", "use_stoch", entry_use_stoch)
                self.config.set_value("entry_preset_stoch_cci", "use_cci", entry_use_cci)
                self.config.set_value("entry_preset_stoch_cci", "basic_indicator", entry_basic_indicator)
                self.config.save()
        if entry_use_stoch == False and entry_use_cci == False:
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])

    def entry_use_stoch_or_rsi_handle(self, entry_rsi_basic_indicator, entry_rsi_use_stoch, entry_rsi_use_rsi):
        lang = self.lang.get()
        if entry_rsi_use_stoch == True and entry_rsi_use_rsi == True:
            if entry_rsi_basic_indicator == "stoch" or entry_rsi_basic_indicator == "rsi":
                self.config.set_value("entry_preset_stoch_rsi", "use_stoch", entry_rsi_use_stoch)
                self.config.set_value("entry_preset_stoch_rsi", "use_rsi", entry_rsi_use_rsi)
                self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", entry_rsi_basic_indicator)
                self.config.save()
        if entry_rsi_use_stoch == False and entry_rsi_use_rsi == True:
            if entry_rsi_basic_indicator == "stoch":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_rsi", "use_stoch", entry_rsi_use_stoch)
                self.config.set_value("entry_preset_stoch_rsi", "use_rsi", entry_rsi_use_rsi)
                self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", entry_rsi_basic_indicator)
                self.config.save()
        if entry_rsi_use_stoch == True and entry_rsi_use_rsi == False:
            if entry_rsi_basic_indicator == "rsi":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_rsi", "use_stoch", entry_rsi_use_stoch)
                self.config.set_value("entry_preset_stoch_rsi", "use_rsi", entry_rsi_use_rsi)
                self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", entry_rsi_basic_indicator)
                self.config.save()
        if entry_rsi_use_stoch == False and entry_rsi_use_rsi == False:
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])


    def entry_basic_indicator_handle(self, entry_basic_indicator, entry_use_stoch, entry_use_cci):
        if entry_use_stoch == True and entry_use_cci == False:
            if entry_basic_indicator == "cci":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_cci", "basic_indicator", entry_basic_indicator)
                self.config.save()
        if entry_use_stoch == False and entry_use_cci == True:
            if entry_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_cci", "basic_indicator", entry_basic_indicator)
                self.config.save()

    def entry_rsi_basic_indicator_handle(self, entry_rsi_basic_indicator, entry_rsi_use_stoch, entry_rsi_use_rsi):
        if entry_rsi_use_stoch == True and entry_rsi_use_rsi == False:
            if entry_rsi_basic_indicator == "rsi":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", entry_rsi_basic_indicator)
                self.config.save()
        if entry_rsi_use_stoch == False and entry_rsi_use_rsi == True:
            if entry_rsi_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", entry_rsi_basic_indicator)
                self.config.save()

    def avg_use_stoch_or_cci_handle(self, avg_basic_indicator, avg_use_stoch, avg_use_cci):
        if avg_use_stoch == True and avg_use_cci == True:
            if avg_basic_indicator == "stoch" or avg_basic_indicator == "cci":
                self.config.set_value("avg_preset_stoch_cci", "basic_indicator", avg_basic_indicator)
                self.config.save()
        if avg_use_stoch == False and avg_use_cci == True:
            if avg_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        if avg_use_stoch == True and avg_use_cci == False:
            if avg_basic_indicator == "cci":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        if avg_use_stoch == False and avg_use_cci == False:
            lang = self.lang.get()
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        else:
            self.config.set_value("avg_preset_stoch_cci", "use_stoch", avg_use_stoch)
            self.config.set_value("avg_preset_stoch_cci", "use_cci", avg_use_cci)
            self.config.save()

    def avg_use_stoch_or_rsi_handle(self, avg_rsi_basic_indicator, avg_rsi_use_stoch, avg_rsi_use_rsi):
        lang = self.lang.get()
        if avg_rsi_use_stoch == True and avg_rsi_use_rsi == True:
            if avg_rsi_basic_indicator == "stoch" or avg_rsi_basic_indicator == "rsi":
                self.config.set_value("avg_preset_stoch_rsi", "use_stoch", avg_rsi_use_stoch)
                self.config.set_value("avg_preset_stoch_rsi", "use_rsi", avg_rsi_use_rsi)
                self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", avg_rsi_basic_indicator)
                self.config.save()
        if avg_rsi_use_stoch == False and avg_rsi_use_rsi == True:
            if avg_rsi_basic_indicator == "stoch":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_rsi", "use_stoch", avg_rsi_use_stoch)
                self.config.set_value("avg_preset_stoch_rsi", "use_rsi", avg_rsi_use_rsi)
                self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", avg_rsi_basic_indicator)
                self.config.save()
        if avg_rsi_use_stoch == True and avg_rsi_use_rsi == False:
            if avg_rsi_basic_indicator == "rsi":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_rsi", "use_stoch", avg_rsi_use_stoch)
                self.config.set_value("avg_preset_stoch_rsi", "use_rsi", avg_rsi_use_rsi)
                self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", avg_rsi_basic_indicator)
                self.config.save()
        if avg_rsi_use_stoch == False and avg_rsi_use_rsi == False:
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])

    def avg_basic_indicator_handle(self, avg_basic_indicator, avg_use_stoch, avg_use_cci):
        if avg_use_stoch == True and avg_use_cci == False:
            if avg_basic_indicator == "cci":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_cci", "basic_indicator", avg_basic_indicator)
                self.config.save()
        if avg_use_stoch == False and avg_use_cci == True:
            if avg_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_cci", "basic_indicator", avg_basic_indicator)
                self.config.save()

    def avg_rsi_basic_indicator_handle(self, avg_rsi_basic_indicator, avg_rsi_use_stoch, avg_rsi_use_rsi):
        if avg_rsi_use_stoch == True and avg_rsi_use_rsi == False:
            if avg_rsi_basic_indicator == "rsi":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", avg_rsi_basic_indicator)
                self.config.save()
        if avg_rsi_use_stoch == False and avg_rsi_use_rsi == True:
            if avg_rsi_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", avg_rsi_basic_indicator)
                self.config.save()

    def exit_use_stoch_or_cci_handle(self, exit_basic_indicator, exit_use_stoch, exit_use_cci):
        if exit_use_stoch == True and exit_use_cci == True:
            if exit_basic_indicator == "stoch" or exit_basic_indicator == "cci":
                self.config.set_value("exit_preset_stoch_cci", "basic_indicator", exit_basic_indicator)
                self.config.save()
        if exit_use_stoch == False and exit_use_cci == True:
            if exit_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        if exit_use_stoch == True and exit_use_cci == False:
            if exit_basic_indicator == "cci":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        if exit_use_stoch == False and exit_use_cci == False:
            lang = self.lang.get()
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
        else:
            self.config.set_value("exit_preset_stoch_cci", "use_stoch", exit_use_stoch)
            self.config.set_value("exit_preset_stoch_cci", "use_cci", exit_use_cci)
            self.config.save()

    def exit_use_stoch_or_rsi_handle(self, exit_rsi_basic_indicator, exit_rsi_use_stoch, exit_rsi_use_rsi):
        lang = self.lang.get()
        if exit_rsi_use_stoch == True and exit_rsi_use_rsi == True:
            if exit_rsi_basic_indicator == "stoch" or exit_rsi_basic_indicator == "rsi":
                self.config.set_value("exit_preset_stoch_rsi", "use_stoch", exit_rsi_use_stoch)
                self.config.set_value("exit_preset_stoch_rsi", "use_rsi", exit_rsi_use_rsi)
                self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", exit_rsi_basic_indicator)
                self.config.save()
        if exit_rsi_use_stoch == False and exit_rsi_use_rsi == True:
            if exit_rsi_basic_indicator == "stoch":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_rsi", "use_stoch", exit_rsi_use_stoch)
                self.config.set_value("exit_preset_stoch_rsi", "use_rsi", exit_rsi_use_rsi)
                self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", exit_rsi_basic_indicator)
                self.config.save()
        if exit_rsi_use_stoch == True and exit_rsi_use_rsi == False:
            if exit_rsi_basic_indicator == "rsi":
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_rsi", "use_stoch", exit_rsi_use_stoch)
                self.config.set_value("exit_preset_stoch_rsi", "use_rsi", exit_rsi_use_rsi)
                self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", exit_rsi_basic_indicator)
                self.config.save()
        if exit_rsi_use_stoch == False and exit_rsi_use_rsi == False:
            messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])

    def exit_basic_indicator_handle(self, exit_basic_indicator, exit_use_stoch, exit_use_cci):
        if exit_use_stoch == True and exit_use_cci == False:
            if exit_basic_indicator == "cci":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_cci", "basic_indicator", exit_basic_indicator)
                self.config.save()
        if exit_use_stoch == False and exit_use_cci == True:
            if exit_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_cci", "basic_indicator", exit_basic_indicator)
                self.config.save()

    def exit_rsi_basic_indicator_handle(self, exit_rsi_basic_indicator, exit_rsi_use_stoch, exit_rsi_use_rsi):
        if exit_rsi_use_stoch == True and exit_use_cci == False:
            if exit_rsi_basic_indicator == "rsi":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", exit_rsi_basic_indicator)
                self.config.save()
        if exit_rsi_use_stoch == False and exit_rsi_use_rsi == True:
            if exit_rsi_basic_indicator == "stoch":
                lang = self.lang.get()
                messagebox.showinfo(message=LANGUAGES[lang]["stoch_cci_incorrect"])
            else:
                self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", exit_rsi_basic_indicator)
                self.config.save()

    def percent_or_amount_handle(self, percent_or_amount):
        #a = self.can_spend.get()
        if percent_or_amount == 1:
            #self.config.set_value("bot", "can_spend", 50)
            self.config.set_value("bot", "percent_or_amount", True)
            self.config.save()
        else:
            #self.config.set_value("bot", "can_spend", a)
            self.config.set_value("bot", "percent_or_amount", False)
            self.config.save()

    def entry_preset_handle(self, entry_preset):
        self.config.set_value("entry", "entry_preset", entry_preset)
        self.config.save()
        entry_cci_cross_use_price = self.entry_cci_cross_use_price.get()

        self.entry_use_stoch_label.grid_forget()
        self.entry_use_stoch_checkbutton.grid_forget()
        self.entry_use_cci_checkbutton.grid_forget()
        self.entry_use_stoch_status_label.grid_forget()
        self.entry_use_cci_status_label.grid_forget()
        self.entry_basic_indicator_label.grid_forget()
        self.entry_basic_indicator_stoch.grid_forget()
        self.entry_basic_indicator_cci.grid_forget()
        self.entry_stoch_up_long_label.grid_forget()
        self.entry_stoch_up_short_label.grid_forget()
        self.entry_stoch_up_long_entry.grid_forget()
        self.entry_stoch_low_long_entry.grid_forget()
        self.entry_stoch_up_short_entry.grid_forget()
        self.entry_stoch_low_short_entry.grid_forget()
        self.entry_cci_level_label.grid_forget()
        self.entry_cci_long_entry.grid_forget()
        self.entry_cci_short_entry.grid_forget()

        self.entry_rsi_use_stoch_label.grid_forget()
        self.entry_rsi_use_stoch_checkbutton.grid_forget()
        self.entry_rsi_use_rsi_checkbutton.grid_forget()
        self.entry_rsi_use_stoch_status_label.grid_forget()
        self.entry_rsi_use_rsi_status_label.grid_forget()
        self.entry_rsi_basic_indicator_label.grid_forget()
        self.entry_rsi_basic_indicator_stoch.grid_forget()
        self.entry_rsi_basic_indicator_rsi.grid_forget()
        self.entry_rsi_stoch_up_long_label.grid_forget()
        self.entry_rsi_stoch_up_short_label.grid_forget()
        self.entry_rsi_stoch_up_long_entry.grid_forget()
        self.entry_rsi_stoch_low_long_entry.grid_forget()
        self.entry_rsi_stoch_up_short_entry.grid_forget()
        self.entry_rsi_stoch_low_short_entry.grid_forget()
        self.entry_rsi_level_label.grid_forget()
        self.entry_rsi_long_entry.grid_forget()
        self.entry_rsi_short_entry.grid_forget()

        self.entry_cci_cross_long_entry.grid_forget()
        self.entry_cci_cross_short_entry.grid_forget()
        self.entry_cci_cross_use_price_label.grid_forget()
        self.entry_cci_cross_use_price_yes.grid_forget()
        self.entry_cci_cross_use_price_no.grid_forget()

        self.entry_ma1_cross_length_label.grid_forget()
        self.entry_ma1_cross_length_entry.grid_forget()
        self.entry_ma2_cross_length_label.grid_forget()
        self.entry_ma2_cross_length_entry.grid_forget()

        self.entry_smarsi_cross_long_label.grid_forget()
        self.entry_smarsi_cross_short_label.grid_forget()
        self.entry_smarsi_cross_up_long_entry.grid_forget()
        self.entry_smarsi_cross_low_long_entry.grid_forget()
        self.entry_smarsi_cross_up_short_entry.grid_forget()
        self.entry_smarsi_cross_low_short_entry.grid_forget()

        self.entry_price_delta_label.grid_forget()
        self.entry_price_delta_short_entry.grid_forget()
        self.entry_price_delta_long_entry.grid_forget()

        # self.entry_qfl_N_label.grid_forget()
        # self.entry_qfl_N_entry.grid_forget()
        # self.entry_qfl_M_label.grid_forget()
        # self.entry_qfl_M_entry.grid_forget()
        # self.entry_qfl_h_l_percent_label.grid_forget()
        # self.entry_qfl_h_l_percent_entry.grid_forget()
        # self.entry_qfl_u_o_label.grid_forget()
        # self.entry_qfl_u_o_list_box.grid_forget()

        if entry_preset == 'STOCH_CCI':
            self.entry_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.entry_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=4, padx=3)
            self.entry_use_stoch_status_label.grid(column=1, row=4, sticky="W", padx=5)
            self.entry_use_cci_checkbutton.grid(column=2, row=4, sticky="W", ipadx=4, padx=2)
            self.entry_use_cci_status_label.grid(column=2, row=4, sticky="W", padx=5)
            self.entry_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.entry_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=5)
            self.entry_basic_indicator_cci.grid(column=2, row=5, sticky="W")

            self.entry_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=0)
            self.entry_stoch_up_short_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.entry_stoch_low_short_entry.grid(column=2, row=6, sticky="W", padx=2)

            self.entry_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=3)
            self.entry_stoch_up_long_entry.grid(column=1, row=7, sticky="W", padx=5)
            self.entry_stoch_low_long_entry.grid(column=2, row=7, sticky="W", padx=2)

            self.entry_cci_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.entry_cci_short_entry.grid(column=1, row=8, sticky="W", padx=5)
            self.entry_cci_long_entry.grid(column=2, row=8, sticky="W", padx=2)

        if entry_preset == 'STOCH_RSI':
            self.entry_rsi_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.entry_rsi_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=4, padx=3)
            self.entry_rsi_use_stoch_status_label.grid(column=1, row=4, sticky="W", padx=5)
            self.entry_rsi_use_rsi_checkbutton.grid(column=2, row=4, sticky="W", ipadx=4, padx=2)
            self.entry_rsi_use_rsi_status_label.grid(column=2, row=4, sticky="W", padx=5)
            self.entry_rsi_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.entry_rsi_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=5)
            self.entry_rsi_basic_indicator_rsi.grid(column=2, row=5, sticky="W")

            self.entry_rsi_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=0)
            self.entry_rsi_stoch_up_short_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.entry_rsi_stoch_low_short_entry.grid(column=2, row=6, sticky="W", padx=2)

            self.entry_rsi_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=3)
            self.entry_rsi_stoch_up_long_entry.grid(column=1, row=7, sticky="W", padx=5)
            self.entry_rsi_stoch_low_long_entry.grid(column=2, row=7, sticky="W", padx=2)

            self.entry_rsi_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.entry_rsi_short_entry.grid(column=1, row=8, sticky="W", padx=5)
            self.entry_rsi_long_entry.grid(column=2, row=8, sticky="W", padx=2)

        if entry_preset == 'CCI_CROSS':
            self.entry_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=2)
            self.entry_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=5)
            self.entry_cci_cross_use_price_no.grid(column=2, row=4, sticky="W")
            self.entry_cci_level_label.grid(column=0, row=5, sticky="W", pady=2)
            self.entry_cci_cross_short_entry.grid(column=1, row=5, sticky="W", padx=5)
            self.entry_cci_cross_long_entry.grid(column=2,  row=5, sticky="W", padx=2)

        if entry_preset == 'MIDAS':
            pass

        if entry_preset == 'MA_CROSS':
            self.entry_ma1_cross_length_label.grid(column=0, row=5, sticky="W", pady=1)
            self.entry_ma1_cross_length_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
            self.entry_ma2_cross_length_label.grid(column=0, row=6, sticky="W", pady=1)
            self.entry_ma2_cross_length_entry.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)

        if entry_preset == 'RSI_SMARSI':
            self.entry_smarsi_cross_short_label.grid(column=0, row=5, sticky="W", pady=1)
            self.entry_smarsi_cross_up_short_entry.grid(column=1, row=5, sticky="W", padx=5)
            self.entry_smarsi_cross_low_short_entry.grid(column=2, row=5, sticky="E", padx=5)

            self.entry_smarsi_cross_long_label.grid(column=0, row=6, sticky="W", pady=1)
            self.entry_smarsi_cross_up_long_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.entry_smarsi_cross_low_long_entry.grid(column=2, row=6, sticky="E", padx=5)

        if entry_preset == 'PRICE':
            self.entry_price_delta_label.grid(column=0, row=4, sticky="W", pady=2)
            self.entry_price_delta_short_entry.grid(column=1, columnspan=2, row=4, sticky="W", pady=2, padx=5)
            self.entry_price_delta_long_entry.grid(column=2, columnspan=2, row=4, sticky="E", padx=5)

    def avg_preset_handle(self, avg_preset):
        self.config.set_value("averaging", "avg_preset", avg_preset)
        self.config.save()
        avg_cci_cross_use_price = self.avg_cci_cross_use_price.get()

        self.avg_use_stoch_label.grid_forget()
        self.avg_use_stoch_checkbutton.grid_forget()
        self.avg_use_cci_checkbutton.grid_forget()
        self.avg_use_stoch_status_label.grid_forget()
        self.avg_use_cci_status_label.grid_forget()
        self.avg_basic_indicator_label.grid_forget()
        self.avg_basic_indicator_stoch.grid_forget()
        self.avg_basic_indicator_cci.grid_forget()
        self.avg_stoch_up_long_label.grid_forget()
        self.avg_stoch_up_long_entry.grid_forget()
        self.avg_stoch_low_long_entry.grid_forget()
        self.avg_stoch_up_short_label.grid_forget()
        self.avg_stoch_up_short_entry.grid_forget()
        self.avg_stoch_low_short_entry.grid_forget()
        self.avg_cci_level_label.grid_forget()
        self.avg_cci_long_entry.grid_forget()
        self.avg_cci_short_entry.grid_forget()

        self.avg_rsi_use_stoch_label.grid_forget()
        self.avg_rsi_use_stoch_checkbutton.grid_forget()
        self.avg_rsi_use_rsi_checkbutton.grid_forget()
        self.avg_rsi_use_stoch_status_label.grid_forget()
        self.avg_rsi_use_rsi_status_label.grid_forget()
        self.avg_rsi_basic_indicator_label.grid_forget()
        self.avg_rsi_basic_indicator_stoch.grid_forget()
        self.avg_rsi_basic_indicator_rsi.grid_forget()
        self.avg_rsi_stoch_up_long_label.grid_forget()
        self.avg_rsi_stoch_up_long_entry.grid_forget()
        self.avg_rsi_stoch_low_long_entry.grid_forget()
        self.avg_rsi_stoch_up_short_label.grid_forget()
        self.avg_rsi_stoch_up_short_entry.grid_forget()
        self.avg_rsi_stoch_low_short_entry.grid_forget()
        self.avg_rsi_level_label.grid_forget()
        self.avg_rsi_long_entry.grid_forget()
        self.avg_rsi_short_entry.grid_forget()

        self.avg_cci_cross_long_entry.grid_forget()
        self.avg_cci_cross_short_entry.grid_forget()
        self.avg_cci_cross_use_price_label.grid_forget()
        self.avg_cci_cross_use_price_yes.grid_forget()
        self.avg_cci_cross_use_price_no.grid_forget()

        self.avg_ma1_cross_length_label.grid_forget()
        self.avg_ma1_cross_length_entry.grid_forget()
        self.avg_ma2_cross_length_label.grid_forget()
        self.avg_ma2_cross_length_entry.grid_forget()

        self.avg_smarsi_cross_long_label.grid_forget()
        self.avg_smarsi_cross_short_label.grid_forget()
        self.avg_smarsi_cross_up_long_entry.grid_forget()
        self.avg_smarsi_cross_low_long_entry.grid_forget()
        self.avg_smarsi_cross_up_short_entry.grid_forget()
        self.avg_smarsi_cross_low_short_entry.grid_forget()

        self.avg_price_delta_label.grid_forget()
        self.avg_price_delta_short_entry.grid_forget()
        self.avg_price_delta_long_entry.grid_forget()

        # self.avg_qfl_N_label.grid_forget()
        # self.avg_qfl_N_entry.grid_forget()
        # self.avg_qfl_M_label.grid_forget()
        # self.avg_qfl_M_entry.grid_forget()
        # self.avg_qfl_h_l_percent_label.grid_forget()
        # self.avg_qfl_h_l_percent_entry.grid_forget()
        # self.avg_qfl_u_o_label.grid_forget()
        # self.avg_qfl_u_o_list_box.grid_forget()

        if avg_preset == 'STOCH_CCI':
            self.avg_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.avg_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=3, pady=1, padx=2)
            self.avg_use_stoch_status_label.grid(column=1, row=4, sticky="W", padx=5)
            self.avg_use_cci_checkbutton.grid(column=2, row=4, sticky="E", pady=1, padx=5)
            self.avg_use_cci_status_label.grid(column=2, row=4, sticky="W")
            self.avg_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.avg_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=6)
            self.avg_basic_indicator_cci.grid(column=2, row=5, sticky="E", padx=5)

            self.avg_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=0)
            self.avg_stoch_up_short_entry.grid(column=1, row=6, sticky="W")
            self.avg_stoch_low_short_entry.grid(column=2, row=6, sticky="E")

            self.avg_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=3)
            self.avg_stoch_up_long_entry.grid(column=1, row=7, sticky="W")
            self.avg_stoch_low_long_entry.grid(column=2, row=7, sticky="E")

            self.avg_cci_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.avg_cci_short_entry.grid(column=1, row=8, sticky="W")
            self.avg_cci_long_entry.grid(column=2, row=8, sticky="E")

        if avg_preset == 'STOCH_RSI':
            self.avg_rsi_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.avg_rsi_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=3, pady=1, padx=2)
            self.avg_rsi_use_stoch_status_label.grid(column=1, row=4, sticky="W", padx=5)
            self.avg_rsi_use_rsi_checkbutton.grid(column=2, row=4, sticky="E", pady=1, padx=5)
            self.avg_rsi_use_rsi_status_label.grid(column=2, row=4, sticky="W")
            self.avg_rsi_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.avg_rsi_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=6)
            self.avg_rsi_basic_indicator_rsi.grid(column=2, row=5, sticky="E", padx=5)

            self.avg_rsi_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=0)
            self.avg_rsi_stoch_up_short_entry.grid(column=1, row=6, sticky="W")
            self.avg_rsi_stoch_low_short_entry.grid(column=2, row=6, sticky="E")

            self.avg_rsi_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=3)
            self.avg_rsi_stoch_up_long_entry.grid(column=1, row=7, sticky="W")
            self.avg_rsi_stoch_low_long_entry.grid(column=2, row=7, sticky="E")

            self.avg_rsi_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.avg_rsi_short_entry.grid(column=1, row=8, sticky="W")
            self.avg_rsi_long_entry.grid(column=2, row=8, sticky="E")

        if avg_preset == 'CCI_CROSS':
            self.avg_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=0)
            self.avg_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=7)
            self.avg_cci_cross_use_price_no.grid(column=2, row=4, sticky="E", padx=5)

            self.avg_cci_level_label.grid(column=0, row=5, sticky="W", pady=2)
            self.avg_cci_cross_short_entry.grid(column=1, row=5, sticky="W")
            self.avg_cci_cross_long_entry.grid(column=2, row=5, sticky="E")
            #self.avg_cci_cross_u_o_label.grid(column=0, row=6, sticky="W", pady=2)
            #self.avg_cci_cross_u_o_list_box.grid(column=1, columnspan=2, row=6, sticky="E")

        if avg_preset == 'MIDAS':
            pass

        if avg_preset == 'MA_CROSS':
            self.avg_ma1_cross_length_label.grid(column=0, row=5, sticky="W", pady=1)
            self.avg_ma1_cross_length_entry.grid(column=1, columnspan=2, row=5, sticky="W")
            self.avg_ma2_cross_length_label.grid(column=0, row=6, sticky="W", pady=1)
            self.avg_ma2_cross_length_entry.grid(column=1, columnspan=2, row=6, sticky="W")
            # self.avg_ma_cross_u_o_label.grid(column=0, row=7, sticky="W", pady=2)
            # self.avg_ma_cross_u_o_list_box.grid(column=1, columnspan=2, row=7, sticky="W")

        if avg_preset == 'RSI_SMARSI':
            self.avg_smarsi_cross_short_label.grid(column=0, row=5, sticky="W", pady=1)
            self.avg_smarsi_cross_up_short_entry.grid(column=1, row=5, sticky="W")
            self.avg_smarsi_cross_low_short_entry.grid(column=2, row=5, sticky="E")

            self.avg_smarsi_cross_long_label.grid(column=0, row=6, sticky="W", pady=1)
            self.avg_smarsi_cross_up_long_entry.grid(column=1, row=6, sticky="W")
            self.avg_smarsi_cross_low_long_entry.grid(column=2, row=6, sticky="E")

        if avg_preset == 'PRICE':
            self.avg_price_delta_label.grid(column=0, row=4, sticky="W", pady=2)
            self.avg_price_delta_short_entry.grid(column=1, columnspan=2, row=4, sticky="W", pady=2)
            self.avg_price_delta_long_entry.grid(column=2, columnspan=2, row=4, sticky="E")

    def exit_preset_handle(self, exit_preset):
        self.config.set_value("exit", "exit_preset", exit_preset)
        self.config.save()
        take_profit = self.take_profit.get()

        self.exit_use_stoch_label.grid_forget()
        self.exit_use_stoch_checkbutton.grid_forget()
        self.exit_use_cci_checkbutton.grid_forget()
        self.exit_use_stoch_status_label.grid_forget()
        self.exit_use_cci_status_label.grid_forget()
        self.exit_basic_indicator_label.grid_forget()
        self.exit_basic_indicator_stoch.grid_forget()
        self.exit_basic_indicator_cci.grid_forget()
        self.exit_stoch_up_long_label.grid_forget()
        self.exit_stoch_up_long_entry.grid_forget()
        self.exit_stoch_low_long_entry.grid_forget()
        self.exit_stoch_up_short_label.grid_forget()
        self.exit_stoch_up_short_entry.grid_forget()
        self.exit_stoch_low_short_entry.grid_forget()
        self.exit_cci_level_label.grid_forget()
        self.exit_cci_long_entry.grid_forget()
        self.exit_cci_short_entry.grid_forget()

        self.exit_rsi_use_stoch_label.grid_forget()
        self.exit_rsi_use_stoch_checkbutton.grid_forget()
        self.exit_rsi_use_rsi_checkbutton.grid_forget()
        self.exit_rsi_use_stoch_status_label.grid_forget()
        self.exit_rsi_use_rsi_status_label.grid_forget()
        self.exit_rsi_basic_indicator_label.grid_forget()
        self.exit_rsi_basic_indicator_stoch.grid_forget()
        self.exit_rsi_basic_indicator_rsi.grid_forget()
        self.exit_rsi_stoch_up_long_label.grid_forget()
        self.exit_rsi_stoch_up_long_entry.grid_forget()
        self.exit_rsi_stoch_low_long_entry.grid_forget()
        self.exit_rsi_stoch_up_short_label.grid_forget()
        self.exit_rsi_stoch_up_short_entry.grid_forget()
        self.exit_rsi_stoch_low_short_entry.grid_forget()
        self.exit_rsi_level_label.grid_forget()
        self.exit_rsi_long_entry.grid_forget()
        self.exit_rsi_short_entry.grid_forget()

        self.exit_cci_cross_long_entry.grid_forget()
        self.exit_cci_cross_short_entry.grid_forget()
        self.exit_cci_cross_use_price_label.grid_forget()
        self.exit_cci_cross_use_price_yes.grid_forget()
        self.exit_cci_cross_use_price_no.grid_forget()

        self.exit_ma1_cross_length_label.grid_forget()
        self.exit_ma1_cross_length_entry.grid_forget()
        self.exit_ma2_cross_length_label.grid_forget()
        self.exit_ma2_cross_length_entry.grid_forget()

        self.exit_smarsi_cross_long_label.grid_forget()
        self.exit_smarsi_cross_short_label.grid_forget()
        self.exit_smarsi_cross_up_long_entry.grid_forget()
        self.exit_smarsi_cross_low_long_entry.grid_forget()
        self.exit_smarsi_cross_up_short_entry.grid_forget()
        self.exit_smarsi_cross_low_short_entry.grid_forget()

        if exit_preset == 'STOCH_CCI' and take_profit == 'indicators_exit':
            self.exit_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.exit_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=4, pady=2, padx=3)
            self.exit_use_stoch_status_label.grid(column=1, row=4, sticky="W", pady=2, padx=5)
            self.exit_use_cci_checkbutton.grid(column=2, row=4, sticky="W", ipadx=4, pady=2, padx=2)
            self.exit_use_cci_status_label.grid(column=2, row=4, sticky="W", padx=5)
            self.exit_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.exit_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=7)
            self.exit_basic_indicator_cci.grid(column=2, row=5, sticky="W", padx=6)

            self.exit_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=2)
            self.exit_stoch_up_short_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.exit_stoch_low_short_entry.grid(column=2, row=6, sticky="W", padx=6)

            self.exit_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=2)
            self.exit_stoch_up_long_entry.grid(column=1, row=7, sticky="W", padx=5)
            self.exit_stoch_low_long_entry.grid(column=2, row=7, sticky="W", padx=6)

            self.exit_cci_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.exit_cci_short_entry.grid(column=1, row=8, sticky="W", padx=5)
            self.exit_cci_long_entry.grid(column=2, row=8, sticky="W", padx=6)

        if exit_preset == 'STOCH_RSI' and take_profit == 'indicators_exit':
            self.exit_rsi_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
            self.exit_rsi_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", ipadx=4, pady=2, padx=3)
            self.exit_rsi_use_stoch_status_label.grid(column=1, row=4, sticky="W", pady=2, padx=5)
            self.exit_rsi_use_rsi_checkbutton.grid(column=2, row=4, sticky="W", ipadx=4, pady=2, padx=2)
            self.exit_rsi_use_rsi_status_label.grid(column=2, row=4, sticky="W", padx=5)
            self.exit_rsi_basic_indicator_label.grid(column=0, row=5, sticky="W")
            self.exit_rsi_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=7)
            self.exit_rsi_basic_indicator_rsi.grid(column=2, row=5, sticky="W", padx=6)

            self.exit_rsi_stoch_up_short_label.grid(column=0, row=6, sticky="W", pady=2)
            self.exit_rsi_stoch_up_short_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.exit_rsi_stoch_low_short_entry.grid(column=2, row=6, sticky="W", padx=6)

            self.exit_rsi_stoch_up_long_label.grid(column=0, row=7, sticky="W", pady=2)
            self.exit_rsi_stoch_up_long_entry.grid(column=1, row=7, sticky="W", padx=5)
            self.exit_rsi_stoch_low_long_entry.grid(column=2, row=7, sticky="W", padx=6)

            self.exit_rsi_level_label.grid(column=0, row=8, sticky="W", pady=0)
            self.exit_rsi_short_entry.grid(column=1, row=8, sticky="W", padx=5)
            self.exit_rsi_long_entry.grid(column=2, row=8, sticky="W", padx=6)

        if exit_preset == 'CCI_CROSS' and take_profit == 'indicators_exit':
            self.exit_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=2)
            self.exit_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=5)
            self.exit_cci_cross_use_price_no.grid(column=2, row=4, sticky="W")
            self.exit_cci_level_label.grid(column=0, row=5, sticky="W", pady=2)
            self.exit_cci_cross_short_entry.grid(column=1, row=5, sticky="W", padx=5)
            self.exit_cci_cross_long_entry.grid(column=2, row=5, sticky="W", padx=5)


        if exit_preset == 'MIDAS' and take_profit == 'indicators_exit':
            pass
            # self.exit_qfl_N_label.grid(column=0, row=4, sticky="W", pady=1)
            # self.exit_qfl_N_entry.grid(column=1, columnspan=2, row=4, sticky="W", padx=5)
            # self.exit_qfl_M_label.grid(column=0, row=5, sticky="W", pady=1)
            # self.exit_qfl_M_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
            # self.exit_qfl_h_l_percent_label.grid(column=0, row=6, sticky="W", pady=1)
            # self.exit_qfl_h_l_percent_entry.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)
            #self.exit_qfl_u_o_label.grid(column=0, row=7, sticky="W", pady=2)
            #self.exit_qfl_u_o_list_box.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)

        if exit_preset == 'MA_CROSS' and take_profit == 'indicators_exit':
            self.exit_ma1_cross_length_label.grid(column=0, row=5, sticky="W", pady=1)
            self.exit_ma1_cross_length_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
            self.exit_ma2_cross_length_label.grid(column=0, row=6, sticky="W", pady=1)
            self.exit_ma2_cross_length_entry.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)
            # self.exit_ma_cross_u_o_label.grid(column=0, row=7, sticky="W", pady=2)
            # self.exit_ma_cross_u_o_list_box.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)

        if exit_preset == 'RSI_SMARSI' and take_profit == 'indicators_exit':
            # SMARSI CROSS
            self.exit_smarsi_cross_short_label.grid(column=0, row=5, sticky="W", pady=1)
            self.exit_smarsi_cross_up_short_entry.grid(column=1, row=5, sticky="W", padx=5)
            self.exit_smarsi_cross_low_short_entry.grid(column=2, row=5, sticky="E", padx=5)

            self.exit_smarsi_cross_long_label.grid(column=0, row=6, sticky="W", pady=1)
            self.exit_smarsi_cross_up_long_entry.grid(column=1, row=6, sticky="W", padx=5)
            self.exit_smarsi_cross_low_long_entry.grid(column=2, row=6, sticky="E", padx=5)

            # self.exit_smarsi_cross_length_label.grid(column=0, row=7, sticky="W", pady=1)
            # self.exit_smarsi_cross_length_entry.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)


    def take_profit_handle(self, take_profit):
        use_dynamic_so = self.use_dynamic_so.get()
        exit_preset = self.exit_preset.get()

        self.exit_conditions_label.grid(column=0, row=0, columnspan=3, sticky="W")
        self.take_profit_label.grid(column=0, row=1, sticky="W", pady=3)
        self.take_profit_list_box.grid(column=1, columnspan=3, row=1, sticky="W", padx=5)


        self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
        self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
        self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

        if take_profit == 'profit_exit':
            self.config.set_value("exit", "take_profit", 'profit_exit')
            self.config.save()
            self.exit_timeframe_label.grid_forget()
            self.exit_timeframe_entry.grid_forget()
            self.exit_preset_label.grid_forget()
            self.exit_preset_list_box.grid_forget()

            self.exit_use_stoch_label.grid_forget()
            self.exit_use_stoch_checkbutton.grid_forget()
            self.exit_use_stoch_status_label.grid_forget()
            self.exit_use_cci_checkbutton.grid_forget()
            self.exit_use_cci_status_label.grid_forget()
            self.exit_basic_indicator_label.grid_forget()
            self.exit_basic_indicator_stoch.grid_forget()
            self.exit_basic_indicator_cci.grid_forget()
            self.exit_stoch_up_long_label.grid_forget()
            self.exit_stoch_up_long_entry.grid_forget()
            self.exit_stoch_low_long_entry.grid_forget()
            self.exit_stoch_up_short_label.grid_forget()
            self.exit_stoch_up_short_entry.grid_forget()
            self.exit_stoch_low_short_entry.grid_forget()
            self.exit_cci_level_label.grid_forget()
            self.exit_cci_long_entry.grid_forget()
            self.exit_cci_short_entry.grid_forget()

            self.exit_rsi_use_stoch_label.grid_forget()
            self.exit_rsi_use_stoch_checkbutton.grid_forget()
            self.exit_rsi_use_stoch_status_label.grid_forget()
            self.exit_rsi_use_rsi_checkbutton.grid_forget()
            self.exit_rsi_use_rsi_status_label.grid_forget()
            self.exit_rsi_basic_indicator_label.grid_forget()
            self.exit_rsi_basic_indicator_stoch.grid_forget()
            self.exit_rsi_basic_indicator_rsi.grid_forget()
            self.exit_rsi_stoch_up_long_label.grid_forget()
            self.exit_rsi_stoch_up_long_entry.grid_forget()
            self.exit_rsi_stoch_low_long_entry.grid_forget()
            self.exit_rsi_stoch_up_short_label.grid_forget()
            self.exit_rsi_stoch_up_short_entry.grid_forget()
            self.exit_rsi_stoch_low_short_entry.grid_forget()
            self.exit_rsi_level_label.grid_forget()
            self.exit_rsi_long_entry.grid_forget()
            self.exit_rsi_short_entry.grid_forget()

            self.exit_cci_cross_long_entry.grid_forget()
            self.exit_cci_cross_short_entry.grid_forget()

            self.exit_cci_cross_use_price_label.grid_forget()
            self.exit_cci_cross_use_price_yes.grid_forget()
            self.exit_cci_cross_use_price_no.grid_forget()


            self.exit_ma1_cross_length_label.grid_forget()
            self.exit_ma1_cross_length_entry.grid_forget()
            self.exit_ma2_cross_length_label.grid_forget()
            self.exit_ma2_cross_length_entry.grid_forget()

            self.exit_smarsi_cross_long_label.grid_forget()
            self.exit_smarsi_cross_short_label.grid_forget()
            self.exit_smarsi_cross_up_long_entry.grid_forget()
            self.exit_smarsi_cross_low_long_entry.grid_forget()
            self.exit_smarsi_cross_up_short_entry.grid_forget()
            self.exit_smarsi_cross_low_short_entry.grid_forget()

            self.squeeze_profit_label.grid_forget()
            self.squeeze_profit_entry.grid_forget()

            self.trailing_stop_label.grid_forget()
            self.trailing_stop_entry.grid_forget()
            self.limit_stop_label.grid_forget()
            self.limit_stop_entry.grid_forget()



        if take_profit == 'indicators_exit':
            self.config.set_value("exit", "take_profit", 'indicators_exit')
            self.config.save()

            self.exit_timeframe_label.grid_forget()
            self.exit_timeframe_entry.grid_forget()
            self.exit_preset_label.grid_forget()
            self.exit_preset_list_box.grid_forget()

            self.exit_use_stoch_label.grid_forget()
            self.exit_use_stoch_checkbutton.grid_forget()
            self.exit_use_stoch_status_label.grid_forget()
            self.exit_use_cci_checkbutton.grid_forget()
            self.exit_use_cci_status_label.grid_forget()
            self.exit_basic_indicator_label.grid_forget()
            self.exit_basic_indicator_stoch.grid_forget()
            self.exit_basic_indicator_cci.grid_forget()
            self.exit_stoch_up_long_label.grid_forget()
            self.exit_stoch_up_long_entry.grid_forget()
            self.exit_stoch_low_long_entry.grid_forget()
            self.exit_stoch_up_short_label.grid_forget()
            self.exit_stoch_up_short_entry.grid_forget()
            self.exit_stoch_low_short_entry.grid_forget()
            self.exit_cci_level_label.grid_forget()
            self.exit_cci_long_entry.grid_forget()
            self.exit_cci_short_entry.grid_forget()

            self.exit_rsi_use_stoch_label.grid_forget()
            self.exit_rsi_use_stoch_checkbutton.grid_forget()
            self.exit_rsi_use_stoch_status_label.grid_forget()
            self.exit_rsi_use_rsi_checkbutton.grid_forget()
            self.exit_rsi_use_rsi_status_label.grid_forget()
            self.exit_rsi_basic_indicator_label.grid_forget()
            self.exit_rsi_basic_indicator_stoch.grid_forget()
            self.exit_rsi_basic_indicator_rsi.grid_forget()
            self.exit_rsi_stoch_up_long_label.grid_forget()
            self.exit_rsi_stoch_up_long_entry.grid_forget()
            self.exit_rsi_stoch_low_long_entry.grid_forget()
            self.exit_rsi_stoch_up_short_label.grid_forget()
            self.exit_rsi_stoch_up_short_entry.grid_forget()
            self.exit_rsi_stoch_low_short_entry.grid_forget()
            self.exit_rsi_level_label.grid_forget()
            self.exit_rsi_long_entry.grid_forget()
            self.exit_rsi_short_entry.grid_forget()

            self.exit_cci_cross_long_entry.grid_forget()
            self.exit_cci_cross_short_entry.grid_forget()

            self.exit_cci_cross_use_price_label.grid_forget()
            self.exit_cci_cross_use_price_yes.grid_forget()
            self.exit_cci_cross_use_price_no.grid_forget()

            self.exit_ma1_cross_length_label.grid_forget()
            self.exit_ma1_cross_length_entry.grid_forget()
            self.exit_ma2_cross_length_label.grid_forget()
            self.exit_ma2_cross_length_entry.grid_forget()

            self.exit_smarsi_cross_long_label.grid_forget()
            self.exit_smarsi_cross_short_label.grid_forget()
            self.exit_smarsi_cross_up_long_entry.grid_forget()
            self.exit_smarsi_cross_low_long_entry.grid_forget()
            self.exit_smarsi_cross_up_short_entry.grid_forget()
            self.exit_smarsi_cross_low_short_entry.grid_forget()

            self.squeeze_profit_label.grid_forget()
            self.squeeze_profit_entry.grid_forget()

            self.trailing_stop_label.grid_forget()
            self.trailing_stop_entry.grid_forget()
            self.limit_stop_label.grid_forget()
            self.limit_stop_entry.grid_forget()


            if exit_preset == 'STOCH_CCI':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=2)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                self.exit_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
                self.exit_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", pady=2, padx=6)
                self.exit_use_stoch_status_label.grid(column=1, row=4, sticky="W", pady=2)
                self.exit_use_cci_checkbutton.grid(column=2, row=4, sticky="W", pady=2, padx=2, ipadx=5)
                self.exit_use_cci_status_label.grid(column=2, row=4, sticky="W")
                self.exit_basic_indicator_label.grid(column=0, row=5, sticky="W")
                self.exit_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=5)
                self.exit_basic_indicator_cci.grid(column=2, row=5, sticky="W", padx=6)
                self.exit_stoch_up_long_label.grid(column=0, row=6, sticky="W", pady=2)
                self.exit_stoch_up_long_entry.grid(column=1, row=6, sticky="W", padx=5)
                self.exit_stoch_low_long_entry.grid(column=2, row=6, sticky="W", padx=8)
                self.exit_stoch_up_short_label.grid(column=0, row=7, sticky="W", pady=2)
                self.exit_stoch_up_short_entry.grid(column=1, row=7, sticky="W", padx=5)
                self.exit_stoch_low_short_entry.grid(column=2, row=7, sticky="W", padx=8)
                self.exit_cci_level_label.grid(column=0, row=8, sticky="W", pady=0)
                self.exit_cci_long_entry.grid(column=1, row=8, sticky="W", padx=5)
                self.exit_cci_short_entry.grid(column=2, row=8, sticky="W", padx=8)

                self.squeeze_profit_label.grid(column=0, row=9, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=2, row=9, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

            if exit_preset == 'STOCH_RSI':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=2)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                self.exit_rsi_use_stoch_label.grid(column=0, row=4, sticky="W", pady=0)
                self.exit_rsi_use_stoch_checkbutton.grid(column=1, row=4, sticky="W", pady=2, padx=6)
                self.exit_rsi_use_stoch_status_label.grid(column=1, row=4, sticky="W", pady=2)
                self.exit_rsi_use_rsi_checkbutton.grid(column=2, row=4, sticky="W", pady=2, padx=2, ipadx=5)
                self.exit_rsi_use_rsi_status_label.grid(column=2, row=4, sticky="W")
                self.exit_rsi_basic_indicator_label.grid(column=0, row=5, sticky="W")
                self.exit_rsi_basic_indicator_stoch.grid(column=1, row=5, sticky="W", padx=5)
                self.exit_rsi_basic_indicator_rsi.grid(column=2, row=5, sticky="W", padx=6)
                self.exit_rsi_stoch_up_long_label.grid(column=0, row=6, sticky="W", pady=2)
                self.exit_rsi_stoch_up_long_entry.grid(column=1, row=6, sticky="W", padx=5)
                self.exit_rsi_stoch_low_long_entry.grid(column=2, row=6, sticky="W", padx=8)
                self.exit_rsi_stoch_up_short_label.grid(column=0, row=7, sticky="W", pady=2)
                self.exit_rsi_stoch_up_short_entry.grid(column=1, row=7, sticky="W", padx=5)
                self.exit_rsi_stoch_low_short_entry.grid(column=2, row=7, sticky="W", padx=8)
                self.exit_rsi_level_label.grid(column=0, row=8, sticky="W", pady=0)
                self.exit_rsi_long_entry.grid(column=1, row=8, sticky="W", padx=5)
                self.exit_rsi_short_entry.grid(column=2, row=8, sticky="W", padx=8)

                self.squeeze_profit_label.grid(column=0, row=9, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=2, row=9, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

            if exit_preset == 'CCI_CROSS':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=3)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                self.exit_cci_cross_use_price_label.grid(column=0, row=4, sticky="W", pady=2)
                self.exit_cci_cross_use_price_yes.grid(column=1, row=4, sticky="W", padx=5)
                self.exit_cci_cross_use_price_no.grid(column=2, row=4, sticky="W")
                self.exit_cci_level_label.grid(column=0, row=5, sticky="W", pady=2)
                self.exit_cci_cross_long_entry.grid(column=1, row=5, sticky="W", padx=5)
                self.exit_cci_cross_short_entry.grid(column=2, row=5, sticky="W", padx=8)
                #self.exit_cci_cross_u_o_label.grid(column=0, row=6, sticky="W", pady=2)
                #self.exit_cci_cross_u_o_list_box.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)

                self.squeeze_profit_label.grid(column=0, row=9, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=2, row=9, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

            if exit_preset == 'MIDAS':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=3)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                # self.exit_qfl_N_label.grid(column=0, row=4, sticky="W", pady=1)
                # self.exit_qfl_N_entry.grid(column=1, columnspan=2, row=4, sticky="W", padx=5)
                # self.exit_qfl_M_label.grid(column=0, row=5, sticky="W", pady=1)
                # self.exit_qfl_M_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
                # self.exit_qfl_h_l_percent_label.grid(column=0, row=6, sticky="W", pady=1)
                # self.exit_qfl_h_l_percent_entry.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)
                #self.exit_qfl_u_o_label.grid(column=0, row=7, sticky="W", pady=2)
                #self.exit_qfl_u_o_list_box.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)

                self.squeeze_profit_label.grid(column=0, row=8, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=3, row=8, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

            if exit_preset == 'MA_CROSS':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=3)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                self.exit_ma1_cross_length_label.grid(column=0, row=5, sticky="W", pady=1)
                self.exit_ma1_cross_length_entry.grid(column=1, columnspan=2, row=5, sticky="W", padx=5)
                self.exit_ma2_cross_length_label.grid(column=0, row=6, sticky="W", pady=1)
                self.exit_ma2_cross_length_entry.grid(column=1, columnspan=2, row=6, sticky="W", padx=5)
                # self.exit_ma_cross_u_o_label.grid(column=0, row=7, sticky="W", pady=2)
                # self.exit_ma_cross_u_o_list_box.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)

                self.squeeze_profit_label.grid(column=0, row=8, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=3, row=8, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)

            if exit_preset == 'RSI_SMARSI':
                self.exit_timeframe_label.grid(column=0, row=2, sticky="W", pady=2)
                self.exit_timeframe_entry.grid(column=1, columnspan=2, row=2, sticky="W", padx=5)
                self.exit_preset_label.grid(column=0, row=3, sticky="W", pady=3)
                self.exit_preset_list_box.grid(column=1, columnspan=2, row=3, sticky="W", padx=5)

                self.exit_smarsi_cross_long_label.grid(column=0, row=5, sticky="W", pady=1)
                self.exit_smarsi_cross_up_long_entry.grid(column=1, row=5, sticky="W", padx=5)
                self.exit_smarsi_cross_low_long_entry.grid(column=2, row=5, sticky="E", padx=5)
                self.exit_smarsi_cross_short_label.grid(column=0, row=6, sticky="W", pady=1)
                self.exit_smarsi_cross_up_short_entry.grid(column=1, row=6, sticky="W", padx=5)
                self.exit_smarsi_cross_low_short_entry.grid(column=2, row=6, sticky="E", padx=5)
                # self.exit_smarsi_cross_length_label.grid(column=0, row=7, sticky="W", pady=1)
                # self.exit_smarsi_cross_length_entry.grid(column=1, columnspan=2, row=7, sticky="W", padx=5)

                self.squeeze_profit_label.grid(column=0, row=8, sticky="W", pady=3)
                self.squeeze_profit_entry.grid(column=1, columnspan=3, row=8, sticky="W", padx=5)
                self.exit_profit_level_label.grid(column=0, row=10, sticky="W", pady=2)
                self.exit_profit_level_entry.grid(column=1, row=10, sticky="W", padx=5)
                self.exit_stop_loss_level_entry.grid(column=2, row=10, sticky="W", padx=8)



    def render_options(self):
        self.general.grid()
        self.strategy.grid()
        self.advanced.grid()
        self.logging_widget.grid()

        use_dynamic_so = self.use_dynamic_so.get()
        entry_preset = self.entry_preset.get()
        avg_preset = self.avg_preset.get()
        exit_preset = self.exit_preset.get()
        take_profit = self.take_profit.get()

        entry_by_indicators = self.entry_by_indicators.get()
        entry_cci_cross_use_price = self.entry_cci_cross_use_price.get()
        avg_cci_cross_use_price = self.avg_cci_cross_use_price.get()
        exit_cci_cross_use_price = self.exit_cci_cross_use_price.get()

        #if exit_preset == 'STOCH_CCI' or exit_preset == 'CCI_CROSS' or exit_preset == 'MA_CROSS' or exit_preset == 'RSI_SMARSI':


        self.entry_cci_cross_use_price_handle(entry_cci_cross_use_price)
        self.avg_cci_cross_use_price_handle(avg_cci_cross_use_price)
        self.exit_cci_cross_use_price_handle(exit_cci_cross_use_price)

        #self.entry_preset_handle(entry_preset)
        self.avg_preset_handle(avg_preset)
        self.exit_preset_handle(exit_preset)

        self.entry_by_indicators_handle(entry_by_indicators)

        self.avg_use_tf_switching_handle(self.avg_use_tf_switching.get())
        self.take_profit_handle(take_profit)
        #self.use_dynamic_so_handle(use_dynamic_so)

        self.render_buttons()

    def create_menu_to_select_coin(self, variable=None):
        #om_select_style = ttk.Style()
        #om_select_style.configure("TMenubutton", background="white", foreground="black", width=6)
        markets = []
        base_coins = self.base_coin.get().replace(' ', '').split(',')
        guote_coins = self.quote_coin.get()
        for i in base_coins:
            markets.append(str(i) + "/" + guote_coins)
        select_coin = ttk.OptionMenu(self.row_32, variable, markets[0], *markets, style="TMenubutton")
        select_coin.pack(side=tk.LEFT, anchor=tk.W, padx=17)
        return select_coin



    def configure(self, config):
        self.config = config

        self.lang.set(config.get_value("bot", "language"))
        lang = self.lang.get()

        self.exchange.set(config.get_value("bot", "exchange"))
        #self.bottype.set(config.get_value("bot", "bottype"))
        #self.market.set(config.get_value("bot", "market"))
        self.base_coin.set(config.get_value("bot", "base_coin"))
        self.quote_coin.set(config.get_value("bot", "quote_coin"))

        self.can_spend.set(config.get_value("bot", "depo"))
        self.percent_or_amount.set(config.get_value("bot", "percent_or_amount"))
        self.bo_amount.set(config.get_value("bot", "bo_amount"))
        #self.so_amount.set(config.get_value("bot", "so_amount"))
        self.leverage.set(config.get_value("bot", "leverage"))
        self.margin_mode.set(config.get_value("bot", "margin_mode"))
        #self.algorithm.set(config.get_value("bot", "algorithm"))
        #self.grow_first.set(config.get_value("bot", "grow_first"))

        #self.log_distribution.set(config.get_value("bot", "log_distribution"))
        #self.log_coeff.set(config.get_value("bot", "log_coeff"))
        self.entry_by_indicators.set(config.get_value("entry", "entry_by_indicators"))

        self.time_sleep.set(config.get_value("bot", "time_sleep"))
        self.time_sleep_coeff.set(config.get_value("bot", "time_sleep_coeff"))
        self.orders_total.set(config.get_value("bot", "orders_total"))
        self.active_orders.set(config.get_value("bot", "active_orders"))
        self.first_step.set(config.get_value("bot", "first_step"))
        self.lift_step.set(config.get_value("bot", "lift_step"))
        self.range_cover.set(config.get_value("bot", "range_cover"))

        self.take_profit.set(config.get_value("exit", "take_profit"))
        #self.trailing_exit.set(config.get_value("exit", "trailing_exit"))
        #self.indicators_exit.set(config.get_value("exit", "indicators_exit"))

        self.squeeze_profit.set(config.get_value("exit", "squeeze_profit"))
        self.trailing_stop.set(config.get_value("exit", "trailing_stop"))
        self.limit_stop.set(config.get_value("exit", "limit_stop"))



        #algorithm = self.algorithm.get()

        #if config.get_value("bot", "active_orders") == 0:
        self.use_dynamic_so.set(True)

        #self.use_dynamic_so.set(config.get_value("bot", "active_orders"))
        self.timeframe.set(config.get_value("averaging", "timeframe"))

        #self.timeframe.set(config.get_value("averaging", "timeframe"))

        self.first_so_coeff.set(config.get_value("bot", "first_so_coeff"))
        self.dynamic_so_coeff.set(config.get_value("bot", "dynamic_so_coeff"))

        #self.one_or_more.set(config.get_value("bot", "one_or_more"))
        self.martingale.set(config.get_value("bot", "martingale"))

        #self.profit.set(config.get_value("bot", "profit"))
        self.cancel_on_trend.set(config.get_value("bot", "cancel_on_trend"))

        self.stoch_fastk_period.set(config.get_value("indicators_tuning", "stoch_fastk_period"))
        self.stoch_slowk_period.set(config.get_value("indicators_tuning", "stoch_slowk_period"))
        self.stoch_slowd_period.set(config.get_value("indicators_tuning", "stoch_slowd_period"))


        self.entry_timeframe.set(config.get_value("entry", "entry_timeframe"))
        self.entry_preset.set(config.get_value("entry", "entry_preset"))



        self.entry_cci_cross_use_price.set(config.get_value("entry_preset_cci_cross", "use_price"))
        self.avg_cci_cross_use_price.set(config.get_value("avg_preset_cci_cross", "use_price"))
        self.exit_cci_cross_use_price.set(config.get_value("exit_preset_cci_cross", "use_price"))

        # self.entry_cci_cross_u_o.set(config.get_value("entry_preset_cci_cross", "cross_method"))
        # self.avg_cci_cross_u_o.set(config.get_value("avg_preset_cci_cross", "cross_method"))
        # self.exit_cci_cross_u_o.set(config.get_value("exit_preset_cci_cross", "cross_method"))

        self.avg_preset.set(config.get_value("averaging", "avg_preset"))


        self.avg_use_tf_switching.set(config.get_value("timeframe_switching", "timeframe_switching"))

        self.exit_timeframe.set(config.get_value("exit", "exit_timeframe"))
        self.exit_preset.set(config.get_value("exit", "exit_preset"))

        self.exit_use_tv_signals.set(config.get_value("exit", "exit_use_tv_signals"))

        self.exit_profit_level.set(config.get_value("exit", "exit_profit_level"))
        self.exit_stop_loss_level.set(config.get_value("exit", "exit_stop_loss_level"))

        # STOCH_CCI
        self.entry_stoch_up_long.set(config.get_value("entry_preset_stoch_cci", "stoch_long_up_level"))
        self.entry_stoch_low_long.set(config.get_value("entry_preset_stoch_cci", "stoch_long_low_level"))
        self.entry_stoch_up_short.set(config.get_value("entry_preset_stoch_cci", "stoch_short_up_level"))
        self.entry_stoch_low_short.set(config.get_value("entry_preset_stoch_cci", "stoch_short_low_level"))
        self.entry_cci_long.set(config.get_value("entry_preset_stoch_cci", "cci_long_level"))
        self.entry_cci_short.set(config.get_value("entry_preset_stoch_cci", "cci_short_level"))
        self.avg_stoch_up_long.set(config.get_value("avg_preset_stoch_cci", "stoch_long_up_level"))
        self.avg_stoch_low_long.set(config.get_value("avg_preset_stoch_cci", "stoch_long_low_level"))
        self.avg_stoch_up_short.set(config.get_value("avg_preset_stoch_cci", "stoch_short_up_level"))
        self.avg_stoch_low_short.set(config.get_value("avg_preset_stoch_cci", "stoch_short_low_level"))
        self.avg_cci_long.set(config.get_value("avg_preset_stoch_cci", "cci_long_level"))
        self.avg_cci_short.set(config.get_value("avg_preset_stoch_cci", "cci_short_level"))
        self.exit_stoch_up_long.set(config.get_value("exit_preset_stoch_cci", "stoch_long_up_level"))
        self.exit_stoch_low_long.set(config.get_value("exit_preset_stoch_cci", "stoch_long_low_level"))
        self.exit_stoch_up_short.set(config.get_value("exit_preset_stoch_cci", "stoch_short_up_level"))
        self.exit_stoch_low_short.set(config.get_value("exit_preset_stoch_cci", "stoch_short_low_level"))
        self.exit_cci_long.set(config.get_value("exit_preset_stoch_cci", "cci_long_level"))
        self.exit_cci_short.set(config.get_value("exit_preset_stoch_cci", "cci_short_level"))

        self.entry_use_stoch.set(config.get_value("entry_preset_stoch_cci", "use_stoch"))
        self.entry_use_cci.set(config.get_value("entry_preset_stoch_cci", "use_cci"))
        self.entry_basic_indicator.set(config.get_value("entry_preset_stoch_cci", "basic_indicator"))
        self.exit_use_stoch.set(config.get_value("exit_preset_stoch_cci", "use_stoch"))
        self.exit_use_cci.set(config.get_value("exit_preset_stoch_cci", "use_cci"))
        self.exit_basic_indicator.set(config.get_value("exit_preset_stoch_cci", "basic_indicator"))
        self.avg_use_stoch.set(config.get_value("avg_preset_stoch_cci", "use_stoch"))
        self.avg_use_cci.set(config.get_value("avg_preset_stoch_cci", "use_cci"))
        self.avg_basic_indicator.set(config.get_value("avg_preset_stoch_cci", "basic_indicator"))

        # STOCH_RSI
        self.entry_rsi_stoch_up_long.set(config.get_value("entry_preset_stoch_rsi", "stoch_long_up_level"))
        self.entry_rsi_stoch_low_long.set(config.get_value("entry_preset_stoch_rsi", "stoch_long_low_level"))
        self.entry_rsi_stoch_up_short.set(config.get_value("entry_preset_stoch_rsi", "stoch_short_up_level"))
        self.entry_rsi_stoch_low_short.set(config.get_value("entry_preset_stoch_rsi", "stoch_short_low_level"))
        self.entry_rsi_long.set(config.get_value("entry_preset_stoch_rsi", "rsi_long_level"))
        self.entry_rsi_short.set(config.get_value("entry_preset_stoch_rsi", "rsi_short_level"))
        self.avg_rsi_stoch_up_long.set(config.get_value("avg_preset_stoch_rsi", "stoch_long_up_level"))
        self.avg_rsi_stoch_low_long.set(config.get_value("avg_preset_stoch_rsi", "stoch_long_low_level"))
        self.avg_rsi_stoch_up_short.set(config.get_value("avg_preset_stoch_rsi", "stoch_short_up_level"))
        self.avg_rsi_stoch_low_short.set(config.get_value("avg_preset_stoch_rsi", "stoch_short_low_level"))
        self.avg_rsi_long.set(config.get_value("avg_preset_stoch_rsi", "rsi_long_level"))
        self.avg_rsi_short.set(config.get_value("avg_preset_stoch_rsi", "rsi_short_level"))
        self.exit_rsi_stoch_up_long.set(config.get_value("exit_preset_stoch_rsi", "stoch_long_up_level"))
        self.exit_rsi_stoch_low_long.set(config.get_value("exit_preset_stoch_rsi", "stoch_long_low_level"))
        self.exit_rsi_stoch_up_short.set(config.get_value("exit_preset_stoch_rsi", "stoch_short_up_level"))
        self.exit_rsi_stoch_low_short.set(config.get_value("exit_preset_stoch_rsi", "stoch_short_low_level"))
        self.exit_rsi_long.set(config.get_value("exit_preset_stoch_rsi", "rsi_long_level"))
        self.exit_rsi_short.set(config.get_value("exit_preset_stoch_rsi", "rsi_short_level"))

        self.entry_rsi_use_stoch.set(config.get_value("avg_preset_stoch_rsi", "use_stoch"))
        self.entry_rsi_use_rsi.set(config.get_value("avg_preset_stoch_rsi", "use_rsi"))
        self.entry_rsi_basic_indicator.set(config.get_value("avg_preset_stoch_rsi", "basic_indicator"))
        self.avg_rsi_use_stoch.set(config.get_value("avg_preset_stoch_rsi", "use_stoch"))
        self.avg_rsi_use_rsi.set(config.get_value("avg_preset_stoch_rsi", "use_rsi"))
        self.avg_rsi_basic_indicator.set(config.get_value("avg_preset_stoch_rsi", "basic_indicator"))
        self.exit_rsi_use_stoch.set(config.get_value("exit_preset_stoch_rsi", "use_stoch"))
        self.exit_rsi_use_rsi.set(config.get_value("exit_preset_stoch_rsi", "use_rsi"))
        self.exit_rsi_basic_indicator.set(config.get_value("exit_preset_stoch_rsi", "basic_indicator"))

        self.use_global_stoch.set(config.get_value("indicators_tuning", "use_global_stoch"))
        self.global_stoch_up_long.set(config.get_value("indicators_tuning", "global_stoch_long_up_level"))
        self.global_stoch_low_long.set(config.get_value("indicators_tuning", "global_stoch_long_low_level"))
        self.global_stoch_up_short.set(config.get_value("indicators_tuning", "global_stoch_short_up_level"))
        self.global_stoch_low_short.set(config.get_value("indicators_tuning", "global_stoch_short_low_level"))


        self.entry_cci_cross_long.set(config.get_value("entry_preset_cci_cross", "cci_long_level"))
        self.entry_cci_cross_short.set(config.get_value("entry_preset_cci_cross", "cci_short_level"))
        self.avg_cci_cross_long.set(config.get_value("avg_preset_cci_cross", "cci_long_level"))
        self.avg_cci_cross_short.set(config.get_value("avg_preset_cci_cross", "cci_short_level"))
        self.exit_cci_cross_long.set(config.get_value("exit_preset_cci_cross", "cci_long_level"))
        self.exit_cci_cross_short.set(config.get_value("exit_preset_cci_cross", "cci_short_level"))

        self.entry_smarsi_cross_up_long.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_long_up_level"))
        self.entry_smarsi_cross_low_long.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_long_low_level"))
        self.entry_smarsi_cross_up_short.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_short_up_level"))
        self.entry_smarsi_cross_low_short.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_short_low_level"))
        # self.entry_smarsi_cross_length.set(config.get_value("entry_preset_rsi_smarsi_cross", "smarsi_length"))

        self.avg_smarsi_cross_up_long.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_long_up_level"))
        self.avg_smarsi_cross_low_long.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_long_low_level"))
        self.avg_smarsi_cross_up_short.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_short_up_level"))
        self.avg_smarsi_cross_low_short.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_short_low_level"))
        # self.avg_smarsi_cross_length.set(config.get_value("avg_preset_rsi_smarsi_cross", "smarsi_length"))

        self.exit_smarsi_cross_up_long.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_long_up_level"))
        self.exit_smarsi_cross_low_long.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_long_low_level"))
        self.exit_smarsi_cross_up_short.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_short_up_level"))
        self.exit_smarsi_cross_low_short.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_short_low_level"))
        # self.exit_smarsi_cross_length.set(config.get_value("exit_preset_rsi_smarsi_cross", "smarsi_length"))

        # PRICE
        self.entry_price_delta_short.set(config.get_value("entry_preset_price", "price_delta_short"))
        self.entry_price_delta_long.set(config.get_value("entry_preset_price", "price_delta_long"))
        self.avg_price_delta_short.set(config.get_value("avg_preset_price", "price_delta_short"))
        self.avg_price_delta_long.set(config.get_value("avg_preset_price", "price_delta_long"))

        # QFL
        # self.entry_qfl_N.set(config.get_value("entry_preset_midas", "N"))
        # self.entry_qfl_M.set(config.get_value("entry_preset_midas", "M"))
        # self.entry_qfl_h_l_percent.set(config.get_value("entry_preset_midas", "h_l_percent"))
        # self.avg_qfl_N.set(config.get_value("avg_preset_midas", "N"))
        # self.avg_qfl_M.set(config.get_value("avg_preset_midas", "M"))
        # self.avg_qfl_h_l_percent.set(config.get_value("avg_preset_midas", "h_l_percent"))
        # self.exit_qfl_N.set(config.get_value("exit_preset_midas", "N"))
        # self.exit_qfl_M.set(config.get_value("exit_preset_midas", "M"))
        # self.exit_qfl_h_l_percent.set(config.get_value("exit_preset_midas", "h_l_percent"))
        # self.entry_qfl_u_o.set(config.get_value("entry_preset_midas", "cross_method"))
        # self.avg_qfl_u_o.set(config.get_value("avg_preset_midas", "cross_method"))
        # self.exit_qfl_u_o.set(config.get_value("exit_preset_midas", "cross_method"))

        # MA_CROSS
        self.entry_ma1_cross_length.set(config.get_value("entry_preset_ma_cross", "ma1_length"))
        self.entry_ma2_cross_length.set(config.get_value("entry_preset_ma_cross", "ma2_length"))
        self.avg_ma1_cross_length.set(config.get_value("avg_preset_ma_cross", "ma1_length"))
        self.avg_ma2_cross_length.set(config.get_value("avg_preset_ma_cross", "ma2_length"))
        self.exit_ma1_cross_length.set(config.get_value("exit_preset_ma_cross", "ma1_length"))
        self.exit_ma2_cross_length.set(config.get_value("exit_preset_ma_cross", "ma2_length"))

        # self.entry_ma_cross_u_o.set(config.get_value("entry_preset_ma_cross", "cross_method"))
        # self.avg_ma_cross_u_o.set(config.get_value("avg_preset_ma_cross", "cross_method"))
        # self.exit_ma_cross_u_o.set(config.get_value("exit_preset_ma_cross", "cross_method"))

        # RSI_SMARSI_CROSS
        # self.entry_smarsi_cross_up_level.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_up_level"))
        # self.entry_smarsi_cross_low_level.set(config.get_value("entry_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_low_level"))
        # self.entry_smarsi_cross_length.set(config.get_value("entry_preset_rsi_smarsi_cross", "smarsi_length"))

        # self.avg_smarsi_cross_up_level.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_up_level"))
        # self.avg_smarsi_cross_low_level.set(config.get_value("avg_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_low_level"))
        # self.avg_smarsi_cross_length.set(config.get_value("avg_preset_rsi_smarsi_cross", "smarsi_length"))

        # self.exit_smarsi_cross_up_level.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_up_level"))
        # self.exit_smarsi_cross_low_level.set(config.get_value("exit_preset_rsi_smarsi_cross", "rsi_"+algorithm+"_low_level"))
        # self.exit_smarsi_cross_length.set(config.get_value("exit_preset_rsi_smarsi_cross", "smarsi_length"))

        self.global_timeframe.set(config.get_value("indicators_tuning", "global_timeframe"))
        self.cci_length.set(config.get_value("indicators_tuning", "cci_length"))
        self.ema200.set(config.get_value("indicators_tuning", "ema200_length"))
        self.ema200_delta.set(config.get_value("indicators_tuning", "ema200_delta"))
        self.macd_f.set(config.get_value("indicators_tuning", "macd_f"))
        self.macd_s.set(config.get_value("indicators_tuning", "macd_s"))
        self.macd_signal.set(config.get_value("indicators_tuning", "macd_signal"))
        self.rsi_length.set(config.get_value("indicators_tuning", "rsi_length"))
        self.atr_length.set(config.get_value("indicators_tuning", "atr_length"))
        self.efi_length.set(config.get_value("indicators_tuning", "efi_length"))
        self.bb_period.set(config.get_value("indicators_tuning", "bb_period"))
        self.bb_dev.set(config.get_value("indicators_tuning", "bb_dev"))
        # self.supertrend_period.set(config.get_value("indicators_tuning", "supertrend_period"))
        # self.supertrend_multiplier.set(config.get_value("indicators_tuning", "supertrend_multiplier"))
        self.ema_global_switch.set(config.get_value("timeframe_switching", "ema_global_switch"))
        self.orders_switch.set(config.get_value("timeframe_switching", "orders_switch"))
        self.orders_count.set(config.get_value("timeframe_switching", "orders_count"))
        self.last_candle_switch.set(config.get_value("timeframe_switching", "last_candle_switch"))
        self.last_candle_count.set(config.get_value("timeframe_switching", "last_candle_count"))
        self.last_candle_orders.set(config.get_value("timeframe_switching", "last_candle_orders"))
        self.stoch_adjustment.set(config.get_value("timeframe_switching", "stoch_adjustment"))

        #self.immediate_so.set(config.get_value("averaging", "immediate_so"))
        self.so_safety_price.set(config.get_value("bot", "so_safety_price"))
        self.emergency_averaging.set(config.get_value("bot", "emergency_averaging"))
        self.back_profit.set(config.get_value("bot", "back_profit"))
        self.use_margin.set(config.get_value("bot", "use_margin"))
        self.margin_top.set(config.get_value("bot", "margin_top"))
        self.margin_bottom.set(config.get_value("bot", "margin_bottom"))

        #connector = Connector()
        #connector.configure(config, self.base_coin.get()[0]+'/'+self.quote_coin.get())

        markets = []
        base_coins = self.base_coin.get().replace(' ', '').split(',')
        guote_coins = self.quote_coin.get()
        for i in base_coins:
            markets.append(str(i) + "/" + guote_coins)

        #market = self.market.get()
        baseCurrency = self.base_coin.get()
        quoteCurrency = self.quote_coin.get()
        self.pair_1.set(baseCurrency)
        self.pair_2.set(quoteCurrency)

        # self.select_coin_variants = base_coins
        # self.select_coin_list_box.set_menu(self.select_coin.get(), *self.select_coin_variants)

        # self.entry_qfl_u_o_variants = ["crossover", "crossunder"]
        # self.entry_qfl_u_o_list_box.set_menu(self.entry_qfl_u_o.get(), *self.entry_qfl_u_o_variants)

        # self.avg_qfl_u_o_variants = ["crossover", "crossunder"]
        # self.avg_qfl_u_o_list_box.set_menu(self.avg_qfl_u_o.get(), *self.avg_qfl_u_o_variants)
        #
        # self.exit_qfl_u_o_variants = ["crossover", "crossunder"]
        # self.exit_qfl_u_o_list_box.set_menu(self.exit_qfl_u_o.get(), *self.exit_qfl_u_o_variants)

        # self.entry_ma_cross_u_o_variants = ["crossover", "crossunder"]
        # self.entry_ma_cross_u_o_list_box.set_menu(self.entry_ma_cross_u_o.get(), *self.entry_ma_cross_u_o_variants)
        #
        # self.avg_ma_cross_u_o_variants = ["crossover", "crossunder"]
        # self.avg_ma_cross_u_o_list_box.set_menu(self.avg_ma_cross_u_o.get(), *self.avg_ma_cross_u_o_variants)
        #
        # self.exit_ma_cross_u_o_variants = ["crossover", "crossunder"]
        # self.exit_ma_cross_u_o_list_box.set_menu(self.exit_ma_cross_u_o.get(), *self.exit_ma_cross_u_o_variants)
        #
        # self.entry_cci_cross_u_o_variants = ["crossover", "crossunder"]
        # self.entry_cci_cross_u_o_list_box.set_menu(self.entry_cci_cross_u_o.get(), *self.entry_cci_cross_u_o_variants)
        #
        # self.avg_cci_cross_u_o_variants = ["crossover", "crossunder"]
        # self.avg_cci_cross_u_o_list_box.set_menu(self.avg_cci_cross_u_o.get(), *self.avg_cci_cross_u_o_variants)
        #
        # self.exit_cci_cross_u_o_variants = ["crossover", "crossunder"]
        # self.exit_cci_cross_u_o_list_box.set_menu(self.exit_cci_cross_u_o.get(), *self.exit_cci_cross_u_o_variants)
        #
        self.entry_preset_variants = ["STOCH_CCI", "STOCH_RSI", "CCI_CROSS", "MA_CROSS", "RSI_SMARSI", "PRICE", "HEDGE"]
        self.entry_preset_list_box.set_menu(self.entry_preset.get(), *self.entry_preset_variants)

        self.avg_preset_variants = ["STOCH_CCI", "STOCH_RSI", "CCI_CROSS", "MA_CROSS", "RSI_SMARSI", "PRICE"]
        self.avg_preset_list_box.set_menu(self.avg_preset.get(), *self.avg_preset_variants)

        self.exit_preset_variants = ["STOCH_CCI", "STOCH_RSI", "CCI_CROSS", "MA_CROSS", "RSI_SMARSI"]
        self.exit_preset_list_box.set_menu(self.exit_preset.get(), *self.exit_preset_variants)

        self.select_profit_variants = ["profit_exit", "indicators_exit"]#"trailing_exit",
        self.take_profit_list_box.set_menu(self.take_profit.get(), *self.select_profit_variants)

        self.margin_mode_variants = ["cross", "isolated"]#"trailing_exit",
        self.margin_mode_list_box.set_menu(self.margin_mode.get(), *self.margin_mode_variants)
        # if algorithm == 'long':
        #     self.select_sma_cross_variants = ["crossunder", "sma_1 > sma 2", "indicators_exit"]
        #     self.sma_cross_list_box.set_menu(self.sma_cross.get(), *self.select_sma_cross_variants)
        # if algorithm == 'short':
        #     self.select_sma_cross_variants = ["crossover", "sma_1 < sma 2", "indicators_exit"]
        #     self.sma_cross_list_box.set_menu(self.sma_cross.get(), *self.select_sma_cross_variants)

        #self.exchange_timeframes = connector.get_available_timeframes()
        #print(self.exchange_timeframes)
        #self.exchange_global_timeframes = self.exchange_timeframes

        # Updating options menu
        #self.timeframe_list_box.set_menu(self.timeframe.get(), *self.exchange_global_timeframes)
        #self.timeframe_list_box.set_menu(self.timeframe.get(), *self.exchange_timeframes)


    def switch_behaviour(self, runned):
        if runned == True:
            self.hide_options()
            self.render_logging_widget()
            self.render_buttons()
            self.disable_all_on_frame(self.row_32)
        elif runned == False:
            self.render_options()
            self.render_buttons()
            self.enable_all_on_frame(self.row_32)
            self.hide_logging_widget()
            #self.use_dynamic_so_handle(self.use_dynamic_so.get())
            #self.take_profit_handle(self.take_profit.get())
            #self.percent_or_amount_handle(self.percent_or_amount.get())
            #self.entry_preset_handle(self.entry_preset.get())
            #self.avg_preset_handle(self.avg_preset.get())
            #self.exit_preset_handle(self.exit_preset.get())
            #self.select_algorithm_handle(self.algorithm.get())

    def disable_all_on_frame(self, frame):
        for child in frame.winfo_children():
            child.configure(state='disable')

    def enable_all_on_frame(self, frame):
        for child in frame.winfo_children():
            child.configure(state='normal')

    def purge_logs(self):
        self.logging_widget.configure(state='normal')
        self.logging_widget.delete('1.0', tk.END)
        self.logging_widget.configure(state='disabled')

    def build(self):
        lang = self.lang.get()
        # Tracing variables
        #self.bottype.trace('w', self.update_text)
        self.base_coin.trace('w', self.update_text)
        self.quote_coin.trace('w', self.update_text)
        #self.one_or_more.trace('w', self.update_text)
        self.percent_or_amount.trace('w', self.update_text)
        self.algorithm.trace('w', self.update_text)
        #self.grow_first.trace('w', self.update_text)
        #self.market.trace('w', self.update_text)
        self.lang.trace('w', self.update_text)
        self.exchange.trace('w', self.update_text)
        #self.use_dynamic_so.trace('w', self.update_text)
        self.use_dynamic_so.trace('w', self.update_text)
        self.entry_by_indicators.trace('w', self.update_text)

        # self.entry_cci_cross_u_o.trace('w', self.update_text)
        # self.avg_cci_cross_u_o.trace('w', self.update_text)
        # self.exit_cci_cross_u_o.trace('w', self.update_text)
        # self.entry_ma_cross_u_o.trace('w', self.update_text)
        # self.avg_ma_cross_u_o.trace('w', self.update_text)
        # self.exit_ma_cross_u_o.trace('w', self.update_text)
        # Create menu
        self.create_menu()

        # Create buttons
        save_button = tk.Button(self.row_32, text=LANGUAGES[lang]["button_save"], width=12, command=self.save_config)
        save_button.pack(side=tk.LEFT, pady=10, padx=7, anchor=tk.W)

        self.update_text()
        self.hide_logging_widget()
        self.render_options()
        self.render_buttons()

        # Hide entries
        #self.take_profit_handle(self.take_profit.get())
        #self.use_dynamic_so_handle(self.use_dynamic_so.get())
        #self.use_dynamic_so_handle(self.use_dynamic_so.get())
        #self.entry_by_indicators_handle(self.entry_by_indicators.get())

        #if now > 1637335800:  #TRIAL
            #messagebox.showinfo(message=LANGUAGES[lang]["trial_ended"])

    def save_config(self):
        dynamic_so = self.use_dynamic_so.get()
        lang = self.lang.get()
        #market = self.market.get()
        base_coin = self.base_coin.get()
        quote_coin = self.quote_coin.get()
        algorithm = self.algorithm.get()
        orders_total = self.orders_total.get()
        time_sleep = self.time_sleep.get()

        match = re.match('[A-Z0-9\,\s]', base_coin)

        if not match:
            messagebox.showinfo(message=LANGUAGES[lang]["market_format_incorrect"])

        if time_sleep < 0.5 or time_sleep > 21600:
            messagebox.showinfo(message=LANGUAGES[lang]["time_sleep_incorrect"])

        # if orders_total < 2 or orders_total > 50:
        #     messagebox.showinfo(message=LANGUAGES[lang]["orders_total_incorrect"])


        if match and (time_sleep >= 0.5 and time_sleep <= 21600) and 1 <= orders_total < 51:
            self.config.set_value("bot", "language", self.lang.get())
            #self.config.set_value("bot", "market", self.market.get())
            #self.config.set_value("bot", "bottype", self.bottype.get())
            self.config.set_value("bot", "base_coin", self.base_coin.get())
            self.config.set_value("bot", "quote_coin", self.quote_coin.get())
            self.config.set_value("bot", "orders_total", self.orders_total.get())
            self.config.set_value("bot", "active_orders", self.active_orders.get())
            self.config.set_value("bot", "time_sleep", self.time_sleep.get())
            self.config.set_value("bot", "range_cover", self.range_cover.get())
            self.config.set_value("bot", "first_step", self.first_step.get())
            self.config.set_value("bot", "lift_step", self.lift_step.get())
            self.config.set_value("bot", "percent_or_amount", self.percent_or_amount.get())
            self.config.set_value("bot", "depo", self.can_spend.get())
            self.config.set_value("bot", "bo_amount", self.bo_amount.get())
            #self.config.set_value("bot", "so_amount", self.so_amount.get())
            self.config.set_value("bot", "leverage", self.leverage.get())
            self.config.set_value("bot", "margin_mode", self.margin_mode.get())
            #self.config.set_value("bot", "use_rsi", self.use_rsi.get())

            self.config.set_value("entry", "entry_by_indicators", self.entry_by_indicators.get())
            self.config.set_value("entry", "entry_timeframe", self.entry_timeframe.get())
            self.config.set_value("entry", "entry_preset", self.entry_preset.get())

            self.config.set_value("entry_preset_stoch_cci", "use_stoch", self.entry_use_stoch.get())
            self.config.set_value("entry_preset_stoch_cci", "use_cci", self.entry_use_cci.get())
            self.config.set_value("entry_preset_stoch_cci", "basic_indicator", self.entry_basic_indicator.get())

            self.config.set_value("entry_preset_stoch_rsi", "use_stoch", self.entry_rsi_use_stoch.get())
            self.config.set_value("entry_preset_stoch_rsi", "use_rsi", self.entry_rsi_use_rsi.get())
            self.config.set_value("entry_preset_stoch_rsi", "basic_indicator", self.entry_rsi_basic_indicator.get())

            self.config.set_value("entry_preset_cci_cross", "use_price", self.entry_cci_cross_use_price.get())

            self.config.set_value("indicators_tuning", "use_global_stoch", self.use_global_stoch.get())
            self.config.set_value("indicators_tuning", "global_timeframe", self.global_timeframe.get())

            # QFL
            # self.config.set_value("entry_preset_midas", "N", self.entry_qfl_N.get())
            # self.config.set_value("entry_preset_midas", "M", self.entry_qfl_M.get())
            # self.config.set_value("entry_preset_midas", "h_l_percent", self.entry_qfl_h_l_percent.get())
            #
            # self.config.set_value("avg_preset_midas", "N", self.avg_qfl_N.get())
            # self.config.set_value("avg_preset_midas", "M", self.avg_qfl_M.get())
            # self.config.set_value("avg_preset_midas", "h_l_percent", self.avg_qfl_h_l_percent.get())
            #
            # self.config.set_value("exit_preset_midas", "N", self.exit_qfl_N.get())
            # self.config.set_value("exit_preset_midas", "M", self.exit_qfl_M.get())
            # self.config.set_value("exit_preset_midas", "h_l_percent", self.exit_qfl_h_l_percent.get())

            #MA_CROSS
            self.config.set_value("entry_preset_ma_cross", "ma1_length", self.entry_ma1_cross_length.get())
            self.config.set_value("entry_preset_ma_cross", "ma2_length", self.entry_ma2_cross_length.get())
            self.config.set_value("avg_preset_ma_cross", "ma1_length", self.avg_ma1_cross_length.get())
            self.config.set_value("avg_preset_ma_cross", "ma2_length", self.avg_ma2_cross_length.get())
            self.config.set_value("exit_preset_ma_cross", "ma1_length", self.exit_ma1_cross_length.get())
            self.config.set_value("exit_preset_ma_cross", "ma2_length", self.exit_ma2_cross_length.get())

            # RSI_SMARSI_CROSS
            # self.config.set_value("entry_preset_rsi_smarsi_cross", "smarsi_length", self.entry_smarsi_cross_length.get())
            #
            # self.config.set_value("avg_preset_rsi_smarsi_cross", "smarsi_length", self.avg_smarsi_cross_length.get())
            #
            # self.config.set_value("exit_preset_rsi_smarsi_cross", "smarsi_length", self.exit_smarsi_cross_length.get())

            self.config.set_value("timeframe_switching", "timeframe_switching", self.avg_use_tf_switching.get())
            self.config.set_value("averaging", "timeframe", self.timeframe.get())
            self.config.set_value("averaging", "avg_preset", self.avg_preset.get())
            self.config.set_value("avg_preset_stoch_cci", "use_stoch", self.avg_use_stoch.get())
            self.config.set_value("avg_preset_stoch_cci", "use_cci", self.avg_use_cci.get())
            self.config.set_value("avg_preset_stoch_cci", "basic_indicator", self.avg_basic_indicator.get())

            self.config.set_value("avg_preset_stoch_rsi", "use_stoch", self.avg_rsi_use_stoch.get())
            self.config.set_value("avg_preset_stoch_rsi", "use_rsi", self.avg_rsi_use_rsi.get())
            self.config.set_value("avg_preset_stoch_rsi", "basic_indicator", self.avg_rsi_basic_indicator.get())

            self.config.set_value("indicators_tuning", "global_timeframe", self.global_timeframe.get())

            self.config.set_value("avg_preset_cci_cross", "use_price", self.avg_cci_cross_use_price.get())

            self.config.set_value("exit", "take_profit", self.take_profit.get())
            self.config.set_value("exit", "squeeze_profit", self.squeeze_profit.get())
            self.config.set_value("exit", "trailing_stop", self.trailing_stop.get())
            self.config.set_value("exit", "limit_stop", self.limit_stop.get())

            self.config.set_value("exit", "exit_profit_level", self.exit_profit_level.get())
            self.config.set_value("exit", "exit_stop_loss_level", self.exit_stop_loss_level.get())

            self.config.set_value("exit", "exit_timeframe", self.exit_timeframe.get())
            self.config.set_value("exit", "exit_use_tv_signals", self.exit_use_tv_signals.get())

            self.config.set_value("exit", "exit_preset", self.exit_preset.get())
            self.config.set_value("exit_preset_stoch_cci", "use_stoch", self.exit_use_stoch.get())
            self.config.set_value("exit_preset_stoch_cci", "use_cci", self.exit_use_cci.get())
            self.config.set_value("exit_preset_stoch_cci", "basic_indicator", self.exit_basic_indicator.get())

            self.config.set_value("exit_preset_stoch_rsi", "use_stoch", self.exit_rsi_use_stoch.get())
            self.config.set_value("exit_preset_stoch_rsi", "use_rsi", self.exit_rsi_use_rsi.get())
            self.config.set_value("exit_preset_stoch_rsi", "basic_indicator", self.exit_rsi_basic_indicator.get())

            self.config.set_value("exit_preset_cci_cross", "use_price", self.exit_cci_cross_use_price.get())

            # self.config.set_value("indicators_tuning", "stoch_fastk_period", self.stoch_fastk_period.get())
            # self.config.set_value("indicators_tuning", "stoch_slowk_period", self.stoch_slowk_period.get())
            # self.config.set_value("indicators_tuning", "stoch_slowd_period", self.stoch_slowd_period.get())

            # self.config.set_value("bot", "algorithm", self.algorithm.get())
            #self.config.set_value("bot", "grow_first", self.grow_first.get())

            #self.config.set_value("bot", "log_distribution", self.log_distribution.get())
            #self.config.set_value("bot", "log_coeff", self.log_coeff.get())
            self.config.set_value("entry", "entry_by_indicators", self.entry_by_indicators.get())

            #self.config.set_value("bot", "one_or_more", self.one_or_more.get())

            #self.config.set_value("entry", "ema200_delta", self.ema200_delta.get())
            self.config.set_value("bot", "first_so_coeff", self.first_so_coeff.get())
            self.config.set_value("bot", "dynamic_so_coeff", self.dynamic_so_coeff.get())

            self.config.set_value("bot", "martingale", self.martingale.get())
            #self.config.set_value("bot", "profit", self.profit.get())

            # self.config.set_value("indicators_tuning", "cci_length", self.cci_length.get())
            # self.config.set_value("indicators_tuning", "ema200_length", self.ema200.get())
            self.config.set_value("indicators_tuning", "ema200_delta", self.ema200_delta.get())
            # self.config.set_value("indicators_tuning", "macd_f", self.macd_f.get())
            # self.config.set_value("indicators_tuning", "macd_s", self.macd_s.get())
            # self.config.set_value("indicators_tuning", "macd_signal", self.macd_signal.get())
            # self.config.set_value("indicators_tuning", "rsi_length", self.rsi_length.get())
            # self.config.set_value("indicators_tuning", "atr_length", self.atr_length.get())
            # self.config.set_value("indicators_tuning", "efi_length", self.efi_length.get())
            # self.config.set_value("indicators_tuning", "bb_period", self.bb_period.get())
            # self.config.set_value("indicators_tuning", "bb_dev", self.bb_dev.get())

            # STOCH_CCI
            self.config.set_value("entry_preset_stoch_cci", "stoch_long_up_level", self.entry_stoch_up_long.get())
            self.config.set_value("entry_preset_stoch_cci", "stoch_long_low_level", self.entry_stoch_low_long.get())
            self.config.set_value("entry_preset_stoch_cci", "stoch_short_up_level", self.entry_stoch_up_short.get())
            self.config.set_value("entry_preset_stoch_cci", "stoch_short_low_level", self.entry_stoch_low_short.get())
            self.config.set_value("entry_preset_stoch_cci", "cci_long_level", self.entry_cci_long.get())
            self.config.set_value("entry_preset_stoch_cci", "cci_short_level", self.entry_cci_short.get())
            self.config.set_value("avg_preset_stoch_cci", "stoch_long_up_level", self.avg_stoch_up_long.get())
            self.config.set_value("avg_preset_stoch_cci", "stoch_long_low_level", self.avg_stoch_low_long.get())
            self.config.set_value("avg_preset_stoch_cci", "stoch_short_up_level", self.avg_stoch_up_short.get())
            self.config.set_value("avg_preset_stoch_cci", "stoch_short_low_level", self.avg_stoch_low_short.get())
            self.config.set_value("avg_preset_stoch_cci", "cci_long_level", self.avg_cci_long.get())
            self.config.set_value("avg_preset_stoch_cci", "cci_short_level", self.avg_cci_short.get())
            self.config.set_value("exit_preset_stoch_cci", "stoch_long_up_level", self.exit_stoch_up_long.get())
            self.config.set_value("exit_preset_stoch_cci", "stoch_long_low_level", self.exit_stoch_low_long.get())
            self.config.set_value("exit_preset_stoch_cci", "stoch_short_up_level", self.exit_stoch_up_short.get())
            self.config.set_value("exit_preset_stoch_cci", "stoch_short_low_level", self.exit_stoch_low_short.get())
            self.config.set_value("exit_preset_stoch_cci", "cci_long_level", self.exit_cci_long.get())
            self.config.set_value("exit_preset_stoch_cci", "cci_short_level", self.exit_cci_short.get())

            # STOCH_RSI
            self.config.set_value("entry_preset_stoch_rsi", "stoch_long_up_level", self.entry_rsi_stoch_up_long.get())
            self.config.set_value("entry_preset_stoch_rsi", "stoch_long_low_level", self.entry_rsi_stoch_low_long.get())
            self.config.set_value("entry_preset_stoch_rsi", "stoch_short_up_level", self.entry_rsi_stoch_up_short.get())
            self.config.set_value("entry_preset_stoch_rsi", "stoch_short_low_level", self.entry_rsi_stoch_low_short.get())
            self.config.set_value("entry_preset_stoch_rsi", "rsi_long_level", self.entry_rsi_long.get())
            self.config.set_value("entry_preset_stoch_rsi", "rsi_short_level", self.entry_rsi_short.get())
            self.config.set_value("avg_preset_stoch_rsi", "stoch_long_up_level", self.avg_rsi_stoch_up_long.get())
            self.config.set_value("avg_preset_stoch_rsi", "stoch_long_low_level", self.avg_rsi_stoch_low_long.get())
            self.config.set_value("avg_preset_stoch_rsi", "stoch_short_up_level", self.avg_rsi_stoch_up_short.get())
            self.config.set_value("avg_preset_stoch_rsi", "stoch_short_low_level", self.avg_rsi_stoch_low_short.get())
            self.config.set_value("avg_preset_stoch_rsi", "rsi_long_level", self.avg_rsi_long.get())
            self.config.set_value("avg_preset_stoch_rsi", "rsi_short_level", self.avg_rsi_short.get())
            self.config.set_value("exit_preset_stoch_rsi", "stoch_long_up_level", self.exit_rsi_stoch_up_long.get())
            self.config.set_value("exit_preset_stoch_rsi", "stoch_long_low_level", self.exit_rsi_stoch_low_long.get())
            self.config.set_value("exit_preset_stoch_rsi", "stoch_short_up_level", self.exit_rsi_stoch_up_short.get())
            self.config.set_value("exit_preset_stoch_rsi", "stoch_short_low_level", self.exit_rsi_stoch_low_short.get())
            self.config.set_value("exit_preset_stoch_rsi", "rsi_long_level", self.exit_rsi_long.get())
            self.config.set_value("exit_preset_stoch_rsi", "rsi_short_level", self.exit_rsi_short.get())


            self.config.set_value("indicators_tuning", "global_stoch_long_up_level", self.global_stoch_up_long.get())
            self.config.set_value("indicators_tuning", "global_stoch_long_low_level", self.global_stoch_low_long.get())
            self.config.set_value("indicators_tuning", "global_stoch_short_up_level", self.global_stoch_up_short.get())
            self.config.set_value("indicators_tuning", "global_stoch_short_low_level", self.global_stoch_low_short.get())
            # self.config.set_value("avg_preset_stoch_cci", "global_stoch_long_up_level", self.avg_global_stoch_up_long.get())
            # self.config.set_value("avg_preset_stoch_cci", "global_stoch_long_low_level", self.avg_global_stoch_low_long.get())
            # self.config.set_value("avg_preset_stoch_cci", "global_stoch_short_up_level", self.avg_global_stoch_up_short.get())
            # self.config.set_value("avg_preset_stoch_cci", "global_stoch_short_low_level", self.avg_global_stoch_low_short.get())

            self.config.set_value("entry_preset_cci_cross", "cci_long_level", self.entry_cci_cross_long.get())
            self.config.set_value("entry_preset_cci_cross", "cci_short_level", self.entry_cci_cross_short.get())
            self.config.set_value("avg_preset_cci_cross", "cci_long_level", self.avg_cci_cross_long.get())
            self.config.set_value("avg_preset_cci_cross", "cci_short_level", self.avg_cci_cross_short.get())
            self.config.set_value("exit_preset_cci_cross", "cci_long_level", self.exit_cci_cross_long.get())
            self.config.set_value("exit_preset_cci_cross", "cci_short_level", self.exit_cci_cross_short.get())

            self.config.set_value("entry_preset_rsi_smarsi_cross", "rsi_long_up_level", self.entry_smarsi_cross_up_long.get())
            self.config.set_value("entry_preset_rsi_smarsi_cross", "rsi_long_low_level", self.entry_smarsi_cross_low_long.get())
            self.config.set_value("entry_preset_rsi_smarsi_cross", "rsi_short_up_level", self.entry_smarsi_cross_up_short.get())
            self.config.set_value("entry_preset_rsi_smarsi_cross", "rsi_short_low_level", self.entry_smarsi_cross_low_short.get())
            # self.config.set_value("entry_preset_rsi_smarsi_cross", "smarsi_length", self.entry_smarsi_cross_length.get())

            self.config.set_value("avg_preset_rsi_smarsi_cross", "rsi_long_up_level", self.avg_smarsi_cross_up_long.get())
            self.config.set_value("avg_preset_rsi_smarsi_cross", "rsi_long_low_level", self.avg_smarsi_cross_low_long.get())
            self.config.set_value("avg_preset_rsi_smarsi_cross", "rsi_short_up_level", self.avg_smarsi_cross_up_short.get())
            self.config.set_value("avg_preset_rsi_smarsi_cross", "rsi_short_low_level", self.avg_smarsi_cross_low_short.get())
            # self.config.set_value("avg_preset_rsi_smarsi_cross", "smarsi_length", self.avg_smarsi_cross_length.get())

            self.config.set_value("exit_preset_rsi_smarsi_cross", "rsi_long_up_level", self.exit_smarsi_cross_up_long.get())
            self.config.set_value("exit_preset_rsi_smarsi_cross", "rsi_long_low_level", self.exit_smarsi_cross_low_long.get())
            self.config.set_value("exit_preset_rsi_smarsi_cross", "rsi_short_up_level", self.exit_smarsi_cross_up_short.get())
            self.config.set_value("exit_preset_rsi_smarsi_cross", "rsi_short_low_level", self.exit_smarsi_cross_low_short.get())
            # self.config.set_value("exit_preset_rsi_smarsi_cross", "smarsi_length", self.exit_smarsi_cross_length.get())

            # PRICE
            self.config.set_value("entry_preset_price", "price_delta_short", self.entry_price_delta_short.get())
            self.config.set_value("entry_preset_price", "price_delta_long", self.entry_price_delta_long.get())
            self.config.set_value("avg_preset_price", "price_delta_short", self.avg_price_delta_short.get())
            self.config.set_value("avg_preset_price", "price_delta_long", self.avg_price_delta_long.get())

            # Save to DB
            MARKETS = []
            base_coins = self.base_coin.get().replace(' ', '').split(',')
            for i in base_coins:
                MARKETS.append(str(i) + "/" + quote_coin)

            for i in MARKETS:
                try:
                    conn = sqlite3.connect('bot.db')
                    cursor = conn.cursor()
                    cursor.execute("""UPDATE counters SET orders_total=:orders_t WHERE counter_market=:counter_market""", {'counter_market': i, 'orders_t': orders_total})
                    conn.commit()
                except Exception as e:
                    print('%s: %s %s' % ('ERROR', type(e).__name__, str(e)))
            self.config.save()



    def hide_logging_widget(self):
        self.row_31.grid_forget()
        self.logging_widget.grid_forget()

    def render_logging_widget(self):
        self.row_31.grid()
        self.logging_widget.grid()

    def render_buttons(self):
        self.row_32.grid_forget()
        self.row_32.grid()

    def hide_options(self):
        self.general.grid_forget()
        self.strategy.grid_forget()
        self.advanced.grid_forget()

    def show_message(self, text):
        tk.messagebox.showinfo(message=text)

    def create_checkbox(self, text=None, variable=None, onvalue=True, offvalue=False, command=None):
        checkbox = tk.Checkbutton(self.row_32, text=text, variable=variable, onvalue=onvalue, offvalue=offvalue, padx=1,
                                  command=command)
        checkbox.pack(side=tk.LEFT)
        return checkbox

    def create_button(self, side=tk.LEFT, removeOnClick=False, text=None, width=None, padx=None, pady=None,
                      command=None):
        def combine_commands(*commands):
            def combined_commands(*args, **kwargs):
                for c in commands:
                    c(*args, **kwargs)

            return combined_commands

        button = tk.Button(self.row_32, text=text, width=width)

        if removeOnClick:
            command = combine_commands(command, button.destroy)

        button['command'] = command
        button.pack(side=side, padx=padx, pady=pady, anchor=tk.W)
        return button

    def create_menu(self):
        lang = self.lang.get()
        menu_bar = tk.Menu(self.master)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        #file_menu.add_command(label="Test", command=lambda: run_task_test())
        #file_menu.add_command(label="Run", command=lambda: run_task_run())
        #file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Language", command=self.select_language)
        menu_bar.add_cascade(label="Options", menu=edit_menu)

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Current settings", command=self.select_settings)
        #settings_menu.add_separator()
        #settings_menu.add_command(label="Trade statistics", command=self.trade_statistics)
        menu_bar.add_cascade(label="Settings", menu=settings_menu)


        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Show statistics", command=self.trade_statistics)
        menu_bar.add_cascade(label="Trade statistics", menu=settings_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Help", command=self.help_index)
        help_menu.add_command(label="About", command=self.about_index)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.master.config(menu=menu_bar)

    def trade_statistics(self):
        pass

    def select_language(self):
        lang_window = tk.Toplevel(self.master)
        lang_window.geometry("160x85")
        select_label = tk.Label(lang_window, text="Select language", padx=37, pady=10)
        select_label.pack(side=tk.TOP, anchor=tk.W)
        button_ru = tk.Button(lang_window, text="RU", padx=5, pady=2, command=lambda: self.select_language_handle('ru'))
        button_en = tk.Button(lang_window, text="EN", padx=5, pady=2, command=lambda: self.select_language_handle('en'))
        button_ru.pack(side=tk.LEFT, anchor=tk.W, padx=27)
        button_en.pack(side=tk.LEFT, anchor=tk.W, padx=8)


    def select_settings(self):
        #market = self.market.get()
        base_coin = self.base_coin.get()
        quote_coin = self.quote_coin.get()
        exchange = self.exchange.get()
        lang = self.lang.get()
        orders_total =  self.orders_total.get()
        #range_cover =  self.range_cover.get()
        #one_or_more =  self.one_or_more.get()

        baseCurrency = base_coin
        quoteCurrency = quote_coin

        use_dynamic_so = self.use_dynamic_so.get()
        percent_or_amount = self.percent_or_amount.get()

        settings_window = tk.Toplevel(self.master)
        settings_window.title("Current settings")

        if use_dynamic_so == 1:
            settings_window.geometry("480x565")
        if use_dynamic_so == 0 :
            settings_window.geometry("480x530")

        self.s_0_label = tk.Label(settings_window)
        self.s_0_label.grid(sticky="W", row=0, column=0)

        self.s_exchange_label = tk.Label(settings_window, text=LANGUAGES[lang]["exchange_label"], padx=20, pady=2)
        self.s_exchange_label.grid(sticky="W", row=1, column=0)

        self.s_t_exchange_label = tk.Label(settings_window, text=exchange, padx=20, pady=2)
        self.s_t_exchange_label.grid(sticky="W", row=1, column=1)

        self.s_base_coin_label = tk.Label(settings_window, text=LANGUAGES[lang]["base_coin_label"], padx=20, pady=2)
        self.s_base_coin_label.grid(sticky="W", row=2, column=0)
        self.s_t_base_coin_label = tk.Label(settings_window, text=self.base_coin.get(), padx=20, pady=2)
        self.s_t_base_coin_label.grid(sticky="W", row=2, column=1)

        self.s_algo_label = tk.Label(settings_window, text=LANGUAGES[lang]["algorithm_label"], padx=20, pady=2)
        self.s_algo_label.grid(sticky="W", row=3, column=0)

        self.s_t_algo_label = tk.Label(settings_window, text=self.algorithm.get(), padx=20, pady=2)
        self.s_t_algo_label.grid(sticky="W", row=3, column=1)

        #algorithm = self.algorithm.get()
        # if algorithm == "long":
        if percent_or_amount == True:
            self.s_can_spend_label = tk.Label(settings_window, text=LANGUAGES[lang]["can_spend_label"] + " " + quoteCurrency + ', %', padx=20, pady=2)
        else:
            self.s_can_spend_label = tk.Label(settings_window, text=LANGUAGES[lang]["can_spend_label"] + " " + quoteCurrency, padx=20, pady=2)

        # else:
        #     if percent_or_amount == True:
        #         self.s_can_spend_label = tk.Label(settings_window, text=LANGUAGES[lang]["can_spend_label"] + " " + baseCurrency + ', %', padx=20, pady=2)
        #     else:
        #         self.s_can_spend_label = tk.Label(settings_window, text=LANGUAGES[lang]["can_spend_label"] + " " + baseCurrency, padx=20, pady=2)

        # self.s_grow_label = tk.Label(settings_window, text=LANGUAGES[lang]["grow_first_label"], padx=20, pady=2)
        # self.s_grow_label.grid(sticky="W", row=4, column=0)
        #
        # if self.grow_first.get() == 1:
        #     var_pair = baseCurrency
        # else:
        #     var_pair = quoteCurrency

        # self.s_t_grow_label = tk.Label(settings_window, text="%s" % var_pair, padx=20, pady=2)
        # self.s_t_grow_label.grid(sticky="W", row=4, column=1)

        self.s_can_spend_label.grid(sticky="W", row=5, column=0)

        self.s_t_can_spend_label = tk.Label(settings_window, text=self.can_spend.get(), padx=20, pady=2)
        self.s_t_can_spend_label.grid(sticky="W", row=5, column=1)

        self.s_first_step_label = tk.Label(settings_window, text=LANGUAGES[lang]["first_step_label"], padx=20, pady=2)
        self.s_first_step_label.grid(sticky="W", row=6, column=0)

        self.s_t_first_step_label = tk.Label(settings_window, text=self.first_step.get(), padx=20, pady=2)
        self.s_t_first_step_label.grid(sticky="W", row=6, column=1)

        self.s_lift_step_label = tk.Label(settings_window, text=LANGUAGES[lang]["lift_step_label"], padx=20, pady=2)
        self.s_lift_step_label.grid(sticky="W", row=7, column=0)

        self.s_t_lift_step_label = tk.Label(settings_window, text=self.lift_step.get(), padx=20, pady=2)
        self.s_t_lift_step_label.grid(sticky="W", row=7, column=1)


        # if self.use_dynamic_so.get() == False:
        #     self.s_range_cover_label = tk.Label(settings_window, text=LANGUAGES[lang]["range_cover_label"], padx=20, pady=2)
        # if self.use_dynamic_so.get() == True:
        #     self.s_range_cover_label = tk.Label(settings_window, text=LANGUAGES[lang]["dynamic_co_label"], padx=20, pady=2)

        if self.use_dynamic_so.get() == False:
            self.s_range_cover_label = tk.Label(settings_window, text=LANGUAGES[lang]["range_cover_label"], padx=20, pady=2)
        if self.use_dynamic_so.get() == True:
            self.s_range_cover_label = tk.Label(settings_window, text=LANGUAGES[lang]["dynamic_so_label"], padx=20, pady=2)

        self.s_range_cover_label.grid(sticky="W", row=8, column=0)

        self.s_t_range_cover_label = tk.Label(settings_window, text=self.range_cover.get(), padx=20, pady=2)
        self.s_t_range_cover_label.grid(sticky="W", row=8, column=1)

        #if self.algorithm.get() == 'long':
        self.s_orders_total_label = tk.Label(settings_window, text=LANGUAGES[lang]["buy_total_label"], padx=20, pady=2)
        # else:
        #     self.s_orders_total_label = tk.Label(settings_window, text=LANGUAGES[lang]["sell_total_label"], padx=20, pady=2)

        self.s_orders_total_label.grid(sticky="W", row=9, column=0)

        self.s_t_orders_total_label = tk.Label(settings_window, text=orders_total, padx=20, pady=2)
        self.s_t_orders_total_label.grid(sticky="W", row=9, column=1)

        # self.s_one_or_more_label = tk.Label(settings_window, text=LANGUAGES[lang]["one_or_more_label"], padx=20, pady=2)
        # self.s_one_or_more_label.grid(sticky="W", row=10, column=0)
        #
        # one = self.one_or_more.get()
        # if one == 0:
        #     one = LANGUAGES[lang]["more_order_label"]
        # #     self.config.set_value("bot", "one_or_more", False)
        # #     self.config.save()
        # else:
        #     one = LANGUAGES[lang]["one_order_label"]
        # #     self.config.set_value("bot", "one_or_more", True)
        # #     self.config.save()

        # self.s_t_one_or_more_label = tk.Label(settings_window, text=one, padx=20, pady=2)
        # self.s_t_one_or_more_label.grid(sticky="W", row=10, column=1)


        use_dynamic_so = self.use_dynamic_so.get()
        # if use_dynamic_so == True:
        #     self.config.set_value("bot", "one_or_more", True)
        #     self.config.save()
        # if use_dynamic_so == False:
        #     self.s_log_distribution_label = tk.Label(settings_window, text=LANGUAGES[lang]["log_distribution_label"], padx=20, pady=2)
        #     self.s_log_distribution_label.grid(sticky="W", row=11, column=0)

        # use_dynamic_so = self.use_dynamic_so.get()
        # if use_dynamic_so == False:
        #     self.s_log_distribution_label = tk.Label(settings_window,
        #                                              text=LANGUAGES[lang]["log_distribution_label"], padx=20,
        #                                              pady=2)
        #     self.s_log_distribution_label.grid(sticky="W", row=11, column=0)
        #
        #     log_distr =self.log_distribution.get()
        #     if log_distr == 1:
        #         log_distr = "yes"
        #     else:
        #         log_distr = "no"
        #     self.s_t_log_distribution_label = tk.Label(settings_window, text=log_distr, padx=20, pady=2)
        #     self.s_t_log_distribution_label.grid(sticky="W", row=11, column=1)

        take_profit = self.take_profit.get()

        self.s_take_profit_label = tk.Label(settings_window, text=LANGUAGES[lang]["take_profit_options_label"], padx=20, pady=2)
        self.s_take_profit_label.grid(sticky="W", row=13, column=0)
        self.s_t_take_profit_label = tk.Label(settings_window, text=take_profit, padx=20, pady=2)
        self.s_t_take_profit_label.grid(sticky="W", row=13, column=1)

        self.s_first_so_koeff_label = tk.Label(settings_window, text=LANGUAGES[lang]["first_so_coeff_label"], padx=20,
                                               pady=2)
        self.s_first_so_koeff_label.grid(sticky="W", row=22, column=0)
        self.s_t_first_so_koeff_label = tk.Label(settings_window, text=self.first_so_coeff.get(), padx=20, pady=2)
        self.s_t_first_so_koeff_label.grid(sticky="W", row=22, column=1)

        self.s_dynamic_so_koef_label = tk.Label(settings_window, text=LANGUAGES[lang]["dynamic_so_coeff_label"],
                                                padx=20, pady=2)
        self.s_dynamic_so_koeff_label.grid(sticky="W", row=23, column=0)
        self.s_t_dynamic_so_koeff_label = tk.Label(settings_window, text=self.dynamic_so_coeff.get(), padx=20, pady=2)
        self.s_t_dynamic_so_koeff_label.grid(sticky="W", row=23, column=1)

        self.s_martingale_label = tk.Label(settings_window, text=LANGUAGES[lang]["martingale_label"], padx=20, pady=2)
        self.s_martingale_label.grid(sticky="W", row=24, column=0)
        self.s_t_martingale_label = tk.Label(settings_window, text=self.martingale.get(), padx=20, pady=2)
        self.s_t_martingale_label.grid(sticky="W", row=24, column=1)


        self.s_squeeze_profit_label = tk.Label(settings_window, text=LANGUAGES[lang]["squeeze_profit_label"], padx=20, pady=2)
        self.s_squeeze_profit_label.grid(sticky="W", row=14, column=0)
        self.s_t_squeeze_profit_label = tk.Label(settings_window, text=self.squeeze_profit.get(), padx=20, pady=2)
        self.s_t_squeeze_profit_label.grid(sticky="W", row=14, column=1)

        if take_profit == 'trailing_exit':
            self.s_trailing_stop_label = tk.Label(settings_window, text=LANGUAGES[lang]["trailing_stop_label"], padx=20, pady=2)
            self.s_trailing_stop_label.grid(sticky="W", row=15, column=0)
            self.s_t_trailing_stop_label = tk.Label(settings_window, text=self.trailing_stop.get(), padx=20, pady=2)
            self.s_t_trailing_stop_label.grid(sticky="W", row=15, column=1)

            self.s_limit_stop_label = tk.Label(settings_window, text=LANGUAGES[lang]["limit_stop_label"], padx=20, pady=2)
            self.s_limit_stop_label.grid(sticky="W", row=16, column=0)
            self.s_t_limit_stop_labell = tk.Label(settings_window, text=self.limit_stop.get(), padx=20, pady=2)
            self.s_t_limit_stop_labell.grid(sticky="W", row=16, column=1)

        if take_profit == 'indicators_exit':


            use_stoch = self.exit_use_stoch.get()
            if use_stoch == 1:
                use_stoch = "yes"
            else:
                use_stoch = "no"

            self.s_exit_use_stoch_label = tk.Label(settings_window, text=LANGUAGES[lang]["exit_use_stoch_label"], padx=20, pady=2)
            self.s_exit_use_stoch_label.grid(sticky="W", row=15, column=0)
            self.s_t_exit_use_stoch_label = tk.Label(settings_window, text=use_stoch, padx=20, pady=2)
            self.s_t_exit_use_stoch_label.grid(sticky="W", row=15, column=1)

            use_cci = self.exit_use_cci.get()
            if use_cci == 1:
                use_cci = "yes"
            else:
                use_cci = "no"
            self.s_exit_use_cci_label = tk.Label(settings_window, text=LANGUAGES[lang]["exit_use_cci_label"], padx=20, pady=2)
            self.s_exit_use_cci_label.grid(sticky="W", row=16, column=0)
            self.s_t_exit_use_cci_label = tk.Label(settings_window, text=use_cci, padx=20, pady=2)
            self.s_t_exit_use_cci_label.grid(sticky="W", row=16, column=1)


            self.s_exit_stoch_up_level_label = tk.Label(settings_window, text=LANGUAGES[lang]["exit_stoch_up_level_label"], padx=20, pady=2)
            self.s_exit_stoch_up_level_label.grid(sticky="W", row=17, column=0)
            self.s_t_exit_stoch_up_level_label = tk.Label(settings_window, text=self.exit_stoch_up_level.get(), padx=20, pady=2)
            self.s_t_exit_stoch_up_level_label.grid(sticky="W", row=17, column=1)


            self.s_exit_cci_level_label = tk.Label(settings_window, text=LANGUAGES[lang]["exit_cci_level_label"], padx=20, pady=2)
            self.s_exit_cci_level_label.grid(sticky="W", row=18, column=0)
            self.s_t_exit_cci_short_level_label = tk.Label(settings_window, text=self.exit_cci_short_level.get(), padx=20, pady=2)
            self.s_t_exit_cci_short_level_label.grid(sticky="W", row=18, column=1)
            self.s_t_exit_cci_long_level_label = tk.Label(settings_window, text=self.exit_cci_long_level.get(), pady=2)
            self.s_t_exit_cci_long_level_label.grid(sticky="W", row=18, column=2)

        if use_dynamic_so == 1:
            use_dynamic_so = "yes"

            self.s_use_dynamic_so_label = tk.Label(settings_window, text=LANGUAGES[lang]["use_dynamic_so_label"], padx=20, pady=2)
            self.s_use_dynamic_so_label.grid(sticky="W", row=19, column=0)
            self.s_t_use_dynamic_so_label = tk.Label(settings_window, text=use_dynamic_so, padx=20, pady=2)
            self.s_t_use_dynamic_so_label.grid(sticky="W", row=19, column=1)

            self.s_timeframe_label = tk.Label(settings_window, text=LANGUAGES[lang]["timeframe_label"], padx=20, pady=2)
            self.s_timeframe_label.grid(sticky="W", row=20, column=0)
            self.s_t_timeframe_label = tk.Label(settings_window, text=self.timeframe.get(), padx=20, pady=2)
            self.s_t_timeframe_label.grid(sticky="W", row=20, column=1)

            self.s_ema200_delta_label = tk.Label(settings_window, text=LANGUAGES[lang]["ema200_delta_label"], padx=20, pady=2)
            self.s_ema200_delta_label.grid(sticky="W", row=21, column=0)
            self.s_t_ema200_delta_label = tk.Label(settings_window, text=self.ema200_delta.get(), padx=20, pady=2)
            self.s_t_ema200_delta_label.grid(sticky="W", row=21, column=1)



            self.s_stoch_fastk_period_label = tk.Label(settings_window, text=LANGUAGES[lang]["stoch_fastk_period_label"], padx=20, pady=2)
            self.s_stoch_fastk_period_label.grid(sticky="W", row=26, column=0)
            self.s_t_stoch_fastk_period_label = tk.Label(settings_window, text=self.stoch_fastk_period.get(), padx=20, pady=2)
            self.s_t_stoch_fastk_period_label.grid(sticky="W", row=26, column=1)
            self.s_t_stoch_slowk_period_label = tk.Label(settings_window, text=self.stoch_slowk_period.get(), pady=2)
            self.s_t_stoch_slowk_period_label.grid(sticky="W", row=26, column=2)
            self.s_t_stoch_slowd_period_label = tk.Label(settings_window, text=self.stoch_slowd_period.get(), padx=40, pady=2)
            self.s_t_stoch_slowd_period_label.grid(sticky="W", row=26, column=3)

            self.s_stoch_level_label = tk.Label(settings_window, text=LANGUAGES[lang]["stoch_level_label"], padx=20, pady=2)
            self.s_stoch_level_label.grid(sticky="W", row=27, column=0)
            self.s_t_stoch_level_label = tk.Label(settings_window, text=self.avg_stoch_up_level.get(), pady=2)
            self.s_t_stoch_level_label.grid(sticky="W", row=27, column=2)


        else:
            use_dynamic_so = "no"

            self.s_use_dynamic_so_label = tk.Label(settings_window, text=LANGUAGES[lang]["use_dynamic_so_label"], padx=20, pady=2)
            self.s_use_dynamic_so_label.grid(sticky="W", row=22, column=0)

            self.s_t_use_dynamic_so_label = tk.Label(settings_window, text=use_dynamic_so, padx=20, pady=2)
            self.s_t_use_dynamic_so_label.grid(sticky="W", row=22, column=1)




        self.s_time_sleep_label = tk.Label(settings_window, text=LANGUAGES[lang]["time_sleep_label"], padx=20, pady=2)
        self.s_time_sleep_label.grid(sticky="W", row=12, column=0)

        self.s_t_time_sleep_label = tk.Label(settings_window, text=self.time_sleep.get(), padx=20, pady=2)
        self.s_t_time_sleep_label.grid(sticky="W", row=12, column=1)



    def help_index(self):
       help_window = tk.Toplevel(self.master)
       help_window.geometry("900x900")
       help_window.title("Help")

       hfbot_title_label = tk.Label(help_window, font="Tahoma 14 bold", text="bot %s for Windows" % APP_VERSION, padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=1, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="bot is an automated cryptocurrency trader built with Python, TA-Lib library, ccxt library", padx=20)
       hfbot_title_label.grid(sticky="W", row=2, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 12 bold", text="Requirements", padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=3, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="Windows x64 (Windows 7 x64, Windows 8.1 x64, Windows 10 x64...)", padx=20)
       hfbot_title_label.grid(sticky="W", row=4, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 12 bold", text="Installation", padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=5, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="Not required", padx=20)
       hfbot_title_label.grid(sticky="W", row=6, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 12 bold", text="How to customize", padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=7, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9 bold", text="Step 1: Open config.toml", padx=40, pady=10)
       hfbot_title_label.grid(sticky="W", row=8, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9 bold", text="Step 2: edit exchange name", padx=40, pady=10)
       hfbot_title_label.grid(sticky="W", row=9, column=0)

       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="[bot]", padx=60)
       hfbot_title_label.grid(sticky="W", row=10, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="...", padx=60)
       hfbot_title_label.grid(sticky="W", row=11, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="exchange = \"binance\"", padx=60)
       hfbot_title_label.grid(sticky="W", row=12, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="...", padx=60)
       hfbot_title_label.grid(sticky="W", row=13, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="")
       hfbot_title_label.grid(sticky="W", row=14, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="alternative exchange names:", padx=40)
       hfbot_title_label.grid(sticky="W", row=15, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="bittrex", padx=60)
       hfbot_title_label.grid(sticky="W", row=16, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="bitfinex", padx=60)
       hfbot_title_label.grid(sticky="W", row=17, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="kraken", padx=60)
       hfbot_title_label.grid(sticky="W", row=18, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="kucoin", padx=60)
       hfbot_title_label.grid(sticky="W", row=19, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="poloniex", padx=60)
       hfbot_title_label.grid(sticky="W", row=20, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="huobipro", padx=60)
       hfbot_title_label.grid(sticky="W", row=21, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="exmo", padx=60)
       hfbot_title_label.grid(sticky="W", row=22, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="upbit", padx=60)
       hfbot_title_label.grid(sticky="W", row=23, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="theocean", padx=60)
       hfbot_title_label.grid(sticky="W", row=24, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="coss", padx=60)
       hfbot_title_label.grid(sticky="W", row=25, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="other exchanges are available here: https://github.com/ccxt/ccxt", padx=40)
       hfbot_title_label.grid(sticky="W", row=26, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 9 bold", text="Step 3: enter your API and API SECRET as in the example:", padx=40, pady=10)
       hfbot_title_label.grid(sticky="W", row=27, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="[binance]", padx=60)
       hfbot_title_label.grid(sticky="W", row=28, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="api_key = \"yiGwTBf3BBG3OmVLiKsdrNizVjAf4M1sRr1jIBgHoQp8rSxSjRMseHDx2SoBsh0U\"", padx=60)
       hfbot_title_label.grid(sticky="W", row=29, column=0)
       hfbot_title_label = tk.Label(help_window, font=('Courier New', 9), text="api_secret = \"AG8fhBcRsDM1v2lWpsVOtkQOlI0BwVuSnDV9TDc6KL4BRlLKe45RDv1mYFIc5OZV\"", padx=60)
       hfbot_title_label.grid(sticky="W", row=30, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 12 bold", text="Uptodate clock", padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=31, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="The clock must be accurate, syncronized to a NTP server (time.nist.gov) very frequently to avoid problems with communication to the exchanges.", padx=20)
       hfbot_title_label.grid(sticky="W", row=32, column=0)

       hfbot_title_label = tk.Label(help_window, font="Tahoma 12 bold", text="Run the bot", padx=20, pady=10)
       hfbot_title_label.grid(sticky="W", row=33, column=0)
       hfbot_title_label = tk.Label(help_window, font="Tahoma 9", text="Run bot.exe", padx=20)
       hfbot_title_label.grid(sticky="W", row=34, column=0)

    def about_index(self):
       about_window = tk.Toplevel(self.master)
       about_window.geometry("250x120")
       about_window.title("About")
       select_label = tk.Label(about_window, text="Name: %s %s \n Website: %s \n Authors: %s" % (APP_NAME, APP_VERSION, APP_WEBSITE, APP_AUTHOR), padx=62, pady=25)
       select_label.pack(side=tk.TOP, anchor=tk.W)


    def update_text(self, *args):
        lang = self.lang.get()
        base_coin = self.base_coin.get()
        quote_coin = self.quote_coin.get()
        #bottype = self.bottype.get()

        # entry_cci_cross_method = self.entry_cci_cross_u_o.get()
        # avg_cci_cross_method = self.avg_cci_cross_u_o.get()
        # exit_cci_cross_method = self.exit_cci_cross_u_o.get()

        # entry_qfl_cross_method = self.entry_qfl_u_o.get()
        # avg_qfl_cross_method = self.avg_qfl_u_o.get()
        # exit_qfl_cross_method = self.exit_qfl_u_o.get()

        # entry_ma_cross_method = self.entry_ma_cross_u_o.get()
        # avg_ma_cross_method = self.avg_ma_cross_u_o.get()
        # exit_ma_cross_method = self.exit_ma_cross_u_o.get()

        MARKETS = []
        base_coins = self.base_coin.get().replace(' ', '').split(',')
        guote_coins = self.quote_coin.get()
        for i in base_coins:
            MARKETS.append(str(i) + "/" + guote_coins)

        #market = self.market.get()
        #one = self.one_or_more.get()
        exchange = self.exchange.get()
        algorithm = self.algorithm.get()
        percent_or_amount = self.percent_or_amount.get()
        use_dynamic_so  = self.use_dynamic_so.get()
        #use_dynamic_so = self.use_dynamic_so.get()

        baseCurrency = MARKETS[0].split('/')[0]
        quoteCurrency = quote_coin

        # if bottype == 'multi':
        market = str(base_coins)+'/'+quoteCurrency
        # else:
        #     market = baseCurrency+'/'+quoteCurrency
        self.master.title('%s, %s (%s) :: %s %s' % (exchange, market, APP_NOTE, APP_NAME, APP_VERSION))
        self.base_coin_label.config(text=LANGUAGES[lang]["market_label"])
        self.separator_label.config(text=' /')
        self.empty_label_1.config(text=' ')
        self.empty_label_2.config(text=' ')
        self.empty_label_3.config(text=' ')
        self.empty_label_4.config(text=' ')
        # self.empty_label_2.config(text=' ')
        # self.empty_label_3.config(text=' ')
        # self.empty_label_4.config(text=' ')
        # self.empty_label_5.config(text=' ')
        # self.empty_label_6.config(text=' ')
        self.percent_or_amount_label.config(text='  %')
        #self.entry_stoch_label.config(text='stoch')
        #self.entry_cci_label.config(text='cci')
        # self.avg_stoch_label.config(text='stoch')
        # self.avg_cci_label.config(text='cci')
        # self.exit_stoch_label.config(text='stoch')
        # self.exit_cci_label.config(text='cci')
        #self.bottype_label.config(text=LANGUAGES[lang]["bottype_label"])
        self.algorithm_label.config(text=LANGUAGES[lang]["algorithm_label"])
        self.margin_mode_label.config(text=LANGUAGES[lang]["margin_mode_label"])
        #self.grow_first_label.config(text=LANGUAGES[lang]["grow_first_label"])

        self.range_cover_label.config(text=LANGUAGES[lang]["range_cover_label"])
        self.cancel_on_trend_label.config(text=LANGUAGES[lang]["cancel_on_trend_label"])

        self.general_settings_label.config(text=LANGUAGES[lang]["general_settings_label"])
        self.entry_conditions_label.config(text=LANGUAGES[lang]["entry_conditions_label"])
        self.averaging_conditions_label.config(text=LANGUAGES[lang]["averaging_conditions_label"])
        self.exit_conditions_label.config(text=LANGUAGES[lang]["exit_conditions_label"])


        self.first_step_label.config(text=LANGUAGES[lang]["first_step_label"])
        self.lift_step_label.config(text=LANGUAGES[lang]["lift_step_label"])

        #self.log_distribution_label.config(text=LANGUAGES[lang]["log_distribution_label"])
        #self.log_coeff_label.config(text=LANGUAGES[lang]["log_distribution_label"])

        self.entry_by_indicators_label.config(text=LANGUAGES[lang]["entry_by_indicators_label"])
        self.entry_timeframe_label.config(text=LANGUAGES[lang]["entry_timeframe_label"])
        self.entry_preset_label.config(text=LANGUAGES[lang]["entry_preset_label"])

        self.entry_basic_indicator_label.config(text=LANGUAGES[lang]["entry_basic_indicator_label"])
        self.entry_stoch_up_long_label.config(text=LANGUAGES[lang]["entry_stoch_up_long_label"])
        self.entry_stoch_up_short_label.config(text=LANGUAGES[lang]["entry_stoch_up_short_label"])
        self.entry_cci_level_label.config(text=LANGUAGES[lang]["entry_cci_level_label"])
        self.entry_use_stoch_label.config(text=LANGUAGES[lang]["entry_use_stoch_or_cci_label"])

        self.entry_rsi_basic_indicator_label.config(text=LANGUAGES[lang]["entry_basic_indicator_label"])
        self.entry_rsi_stoch_up_long_label.config(text=LANGUAGES[lang]["entry_stoch_up_long_label"])
        self.entry_rsi_stoch_up_short_label.config(text=LANGUAGES[lang]["entry_stoch_up_short_label"])
        self.entry_rsi_level_label.config(text=LANGUAGES[lang]["entry_rsi_level_label"])
        self.entry_rsi_use_stoch_label.config(text=LANGUAGES[lang]["entry_use_stoch_or_rsi_label"])

        # self.entry_use_global_stoch_label.config(text=LANGUAGES[lang]["use_global_timeframe_label"])

        # self.entry_global_stoch_level_label.config(text=LANGUAGES[lang]["entry_global_stoch_level_label"])
        #
        self.avg_use_tf_switching_label.config(text=LANGUAGES[lang]["avg_use_tf_switching_label"])
        self.timeframe_label.config(text=LANGUAGES[lang]["avg_timeframes_label"])
        self.avg_preset_label.config(text=LANGUAGES[lang]["avg_preset_label"])
        self.avg_basic_indicator_label.config(text=LANGUAGES[lang]["avg_basic_indicator_label"])
        self.avg_stoch_up_long_label.config(text=LANGUAGES[lang]["avg_stoch_up_long_label"])
        self.avg_stoch_up_short_label.config(text=LANGUAGES[lang]["avg_stoch_up_short_label"])

        self.avg_cci_level_label.config(text=LANGUAGES[lang]["avg_cci_level_label"])
        self.avg_use_stoch_label.config(text=LANGUAGES[lang]["avg_use_stoch_or_cci_label"])

        self.avg_rsi_basic_indicator_label.config(text=LANGUAGES[lang]["avg_basic_indicator_label"])
        self.avg_rsi_stoch_up_long_label.config(text=LANGUAGES[lang]["avg_stoch_up_long_label"])
        self.avg_rsi_stoch_up_short_label.config(text=LANGUAGES[lang]["avg_stoch_up_short_label"])
        self.avg_rsi_level_label.config(text=LANGUAGES[lang]["avg_rsi_level_label"])
        self.avg_rsi_use_stoch_label.config(text=LANGUAGES[lang]["avg_use_stoch_or_rsi_label"])

        # self.avg_use_global_stoch_label.config(text=LANGUAGES[lang]["use_global_timeframe_label"])
        # self.avg_global_stoch_level_label.config(text=LANGUAGES[lang]["avg_global_stoch_level_label"])

        self.exit_timeframe_label.config(text=LANGUAGES[lang]["exit_timeframe_label"])
        self.exit_preset_label.config(text=LANGUAGES[lang]["exit_preset_label"])
        self.exit_basic_indicator_label.config(text=LANGUAGES[lang]["exit_basic_indicator_label"])
        self.exit_stoch_up_long_label.config(text=LANGUAGES[lang]["exit_stoch_up_long_label"])
        self.exit_stoch_up_short_label.config(text=LANGUAGES[lang]["exit_stoch_up_short_label"])

        self.exit_cci_level_label.config(text=LANGUAGES[lang]["exit_cci_level_label"])
        self.exit_use_stoch_label.config(text=LANGUAGES[lang]["exit_use_stoch_or_cci_label"])

        self.exit_rsi_level_label.config(text=LANGUAGES[lang]["exit_rsi_level_label"])
        self.exit_rsi_use_stoch_label.config(text=LANGUAGES[lang]["exit_use_stoch_or_rsi_label"])

        self.exit_rsi_basic_indicator_label.config(text=LANGUAGES[lang]["exit_basic_indicator_label"])
        self.exit_rsi_stoch_up_long_label.config(text=LANGUAGES[lang]["exit_stoch_up_long_label"])
        self.exit_rsi_stoch_up_short_label.config(text=LANGUAGES[lang]["exit_stoch_up_short_label"])
        self.exit_rsi_level_label.config(text=LANGUAGES[lang]["exit_rsi_level_label"])
        self.exit_rsi_use_stoch_label.config(text=LANGUAGES[lang]["exit_use_stoch_or_rsi_label"])

        self.entry_cci_cross_use_price_label.config(text=LANGUAGES[lang]["use_price_label"])
        self.avg_cci_cross_use_price_label.config(text=LANGUAGES[lang]["use_price_label"])
        self.exit_cci_cross_use_price_label.config(text=LANGUAGES[lang]["use_price_label"])

        # if entry_cci_cross_method == 'crossover':
        #     self.entry_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.entry_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])
        #
        # if avg_cci_cross_method == 'crossover':
        #     self.avg_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.avg_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])
        #
        # if exit_cci_cross_method == 'crossover':
        #     self.exit_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.exit_cci_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])


        # QFL
        # self.entry_qfl_N_label.config(text=LANGUAGES[lang]["qfl_N_label"])
        # self.entry_qfl_M_label.config(text=LANGUAGES[lang]["qfl_M_label"])
        # self.entry_qfl_h_l_percent_label.config(text=LANGUAGES[lang]["1_qfl_h_l_percent_label"])
        # if entry_qfl_cross_method == 'crossover':
        #     self.entry_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.entry_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])

        # self.avg_qfl_N_label.config(text=LANGUAGES[lang]["qfl_N_label"])
        # self.avg_qfl_M_label.config(text=LANGUAGES[lang]["qfl_M_label"])
        # self.avg_qfl_h_l_percent_label.config(text=LANGUAGES[lang]["1_qfl_h_l_percent_label"])
        # if avg_ma_cross_method == 'crossover':
        #     self.avg_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.avg_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])

        # self.exit_qfl_N_label.config(text=LANGUAGES[lang]["qfl_N_label"])
        # self.exit_qfl_M_label.config(text=LANGUAGES[lang]["qfl_M_label"])
        # self.exit_qfl_h_l_percent_label.config(text=LANGUAGES[lang]["2_qfl_h_l_percent_label"])
        # if exit_qfl_cross_method == 'crossover':
        #     self.exit_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.exit_qfl_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])


        # MA_CROSS
        self.entry_ma1_cross_length_label.config(text=LANGUAGES[lang]["ma1_cross_length_label"])
        self.entry_ma2_cross_length_label.config(text=LANGUAGES[lang]["ma2_cross_length_label"])

        # if entry_ma_cross_method == 'crossover':
        #     self.entry_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.entry_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])

        self.avg_ma1_cross_length_label.config(text=LANGUAGES[lang]["ma1_cross_length_label"])
        self.avg_ma2_cross_length_label.config(text=LANGUAGES[lang]["ma2_cross_length_label"])
        # if avg_ma_cross_method == 'crossover':
        #     self.avg_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.avg_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])

        self.exit_ma1_cross_length_label.config(text=LANGUAGES[lang]["ma1_cross_length_label"])
        self.exit_ma2_cross_length_label.config(text=LANGUAGES[lang]["ma2_cross_length_label"])
        # if exit_ma_cross_method == 'crossover':
        #     self.exit_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossover"])
        # else:
        #     self.exit_ma_cross_u_o_label.config(text=LANGUAGES[lang]["cci_cross_crossunder"])

        self.entry_smarsi_cross_long_label.config(text=LANGUAGES[lang]["rsi_level_long"])
        self.entry_smarsi_cross_short_label.config(text=LANGUAGES[lang]["rsi_level_short"])
        # self.entry_smarsi_cross_length_label.config(text=LANGUAGES[lang]["smarsi_length_label"])
        self.avg_smarsi_cross_long_label.config(text=LANGUAGES[lang]["rsi_level_long"])
        self.avg_smarsi_cross_short_label.config(text=LANGUAGES[lang]["rsi_level_short"])
        # self.avg_smarsi_cross_length_label.config(text=LANGUAGES[lang]["smarsi_length_label"])
        self.exit_smarsi_cross_long_label.config(text=LANGUAGES[lang]["rsi_level_long"])
        self.exit_smarsi_cross_short_label.config(text=LANGUAGES[lang]["rsi_level_short"])
        # self.exit_smarsi_cross_length_label.config(text=LANGUAGES[lang]["smarsi_length_label"])

        self.indicators_fine_tuning_label.config(text=LANGUAGES[lang]["indicators_fine_tuning_label"])
        self.global_timeframe_label.config(text=LANGUAGES[lang]["global_timeframe_label"])
        self.use_stoch_rsi_label.config(text=LANGUAGES[lang]["use_stoch_rsi"])
        # self.stoch_fastk_period_label.config(text=LANGUAGES[lang]["stoch_fastk_period_label"])
        # self.cci_length_label.config(text=LANGUAGES[lang]["cci_length_label"])
        # self.ema200_and_delta_label.config(text=LANGUAGES[lang]["ema200_and_delta_label"])
        # self.macd_label.config(text=LANGUAGES[lang]["macd_label"])
        # self.rsi_atr_efi_length_label.config(text=LANGUAGES[lang]["rsi_atr_efi_length_label"])
        #self.bb_label.config(text=LANGUAGES[lang]["bb_label"])
        #self.supertrend_label.config(text=LANGUAGES[lang]["supertrend_label"])

        self.use_global_stoch_label.config(text=LANGUAGES[lang]["use_global_stoch_label"])
        self.global_stoch_long_label.config(text=LANGUAGES[lang]["global_stoch_long_label"])
        self.global_stoch_short_label.config(text=LANGUAGES[lang]["global_stoch_short_label"])

        self.timeframe_switching_label.config(text=LANGUAGES[lang]["timeframe_switching_label"])
        self.ema_global_switch_label.config(text=LANGUAGES[lang]["ema_global_switch_label"])
        self.orders_switch_label.config(text=LANGUAGES[lang]["orders_switch_label"])
        self.orders_count_label.config(text=LANGUAGES[lang]["orders_count_label"])
        self.last_candle_switch_label.config(text=LANGUAGES[lang]["last_candle_switch_label"])
        self.last_candle_count_label.config(text=LANGUAGES[lang]["last_candle_count_label"])
        self.stoch_adjustment_label.config(text=LANGUAGES[lang]["stoch_adjustment_label"])

        self.miscellaneous_label.config(text=LANGUAGES[lang]["miscellaneous_label"])
        #self.immediate_so_label.config(text=LANGUAGES[lang]["immediate_so_label"])
        self.so_safety_price_label.config(text=LANGUAGES[lang]["so_safety_price_label"])
        self.emergency_averaging_label.config(text=LANGUAGES[lang]["emergency_averaging_label"])
        self.back_profit_label.config(text=LANGUAGES[lang]["back_profit_label"])
        self.use_margin_label.config(text=LANGUAGES[lang]["use_margin_label"])
        self.margin_top_and_bottom_label.config(text=LANGUAGES[lang]["margin_top_and_bottom_label"])
        #self.exit_use_global_stoch_label.config(text=LANGUAGES[lang]["use_global_timeframe_label"])
        #self.exit_global_stoch_level_label.config(text=LANGUAGES[lang]["exit_global_stoch_level_label"])
        #self.use_dynamic_so_label.config(text=LANGUAGES[lang]["use_dynamic_so_label"])
        #if self.algorithm.get() == 'long':
            #self.trailing_label.config(text=LANGUAGES[lang]["trailing_label_long"])
        #if self.algorithm.get() == 'short':
            #self.trailing_label.config(text=LANGUAGES[lang]["trailing_label_short"])
        self.take_profit_label.config(text=LANGUAGES[lang]["take_profit_options_label"])
        self.squeeze_profit_label.config(text=LANGUAGES[lang]["squeeze_profit_label"])
        self.exit_profit_level_label.config(text=LANGUAGES[lang]["exit_profit_level_label"])
        self.trailing_stop_label.config(text=LANGUAGES[lang]["trailing_stop_label"])
        self.limit_stop_label.config(text=LANGUAGES[lang]["limit_stop_label"])
        #self.supertrend_label.config(text=LANGUAGES[lang]["supertrend_label"])
        self.use_dynamic_so_label.config(text=LANGUAGES[lang]["use_dynamic_so_label"])
        # #self.timeframe_label.config(text=LANGUAGES[lang]["timeframe_label"])
        self.first_so_coeff_label.config(text=LANGUAGES[lang]["first_so_coeff_label"])
        self.dynamic_so_coeff_label.config(text=LANGUAGES[lang]["dynamic_so_coeff_label"])

        #self.one_or_more_label.config(text=LANGUAGES[lang]["one_or_more_label"])
        self.back_profit_label.config(text=LANGUAGES[lang]["back_profit_label"])
        self.so_safety_price_label.config(text=LANGUAGES[lang]["so_safety_price_label"])
        self.emergency_averaging_label.config(text=LANGUAGES[lang]["emergency_averaging_label"])
        self.use_margin_label.config(text=LANGUAGES[lang]["use_margin_label"])

        self.martingale_label.config(text=LANGUAGES[lang]["martingale_label"])
        self.time_sleep_label.config(text=LANGUAGES[lang]["time_sleep_label"])

        self.orders_total_label.config(text=LANGUAGES[lang]["buy_total_label"])
        self.active_orders_label.config(text=LANGUAGES[lang]["buy_active_label"])


        # PRICE
        self.entry_price_delta_label.config(text=LANGUAGES[lang]["price_delta_label"])
        self.avg_price_delta_label.config(text=LANGUAGES[lang]["avg_price_delta_label"])

        # if self.algorithm.get() == 'short':
        # if percent_or_amount == True:
        #     self.can_spend_label.config(text="%s %s %s" % (LANGUAGES[lang]["can_spend_label"], baseCurrency,", %"))
        # else:
        #     self.can_spend_label.config(text="%s %s" % (LANGUAGES[lang]["can_spend_label"], baseCurrency))
        # else:
        if percent_or_amount == True:
            self.can_spend_label.config(text="%s %s %s" % (LANGUAGES[lang]["can_spend_label"], quoteCurrency,", %"))
            self.bo_amount_label.config(text="%s %s" % (LANGUAGES[lang]["bo_amount_label"], ", %"))
            #self.so_amount_label.config(text="%s %s" % (LANGUAGES[lang]["so_amount_label"], ", %"))
        else:
            self.can_spend_label.config(text="%s %s" % (LANGUAGES[lang]["can_spend_label"], quoteCurrency))
            self.bo_amount_label.config(text="%s" % (LANGUAGES[lang]["bo_amount_label"]))
            #self.so_amount_label.config(text="%s" % (LANGUAGES[lang]["so_amount_label"]))
        self.leverage_label.config(text=LANGUAGES[lang]["leverage_label"])


        # TOOL TIPS
        # if self.bottype.get() == 'single':
        #     self.bottype_ttp = CreateToolTip(self.bottype_label, LANGUAGES[lang]["bottype_label_single_definition"])
        # else:
        #     self.bottype_ttp = CreateToolTip(self.bottype_label, LANGUAGES[lang]["bottype_label_multi_definition"])

        self.base_coin_ttp = CreateToolTip(self.base_coin_label, LANGUAGES[lang]["market_definition"])


        self.orders_total_ttp = CreateToolTip(self.orders_total_label, LANGUAGES[lang]["buy_total_definition"])
        self.first_step_ttp = CreateToolTip(self.first_step_label, LANGUAGES[lang]["first_step_definition"])
        self.lift_step_ttp = CreateToolTip(self.lift_step_label, LANGUAGES[lang]["lift_step_definition"])

        # if self.grow_first.get() == True:
        #     self.grow_first_ttp = CreateToolTip(self.grow_first_label, LANGUAGES[lang]["grow_first_1_definition"]+" "+baseCurrency)
        # else:
        #     self.grow_first_ttp = CreateToolTip(self.grow_first_label, LANGUAGES[lang]["grow_first_2_definition"]+" "+quoteCurrency)

        if percent_or_amount == True:
            self.can_spend_ttp = CreateToolTip(self.can_spend_label, LANGUAGES[lang]["can_spend_first_currency_percent_definition"])
        else:
            self.can_spend_ttp = CreateToolTip(self.can_spend_label, LANGUAGES[lang]["can_spend_first_currency_coin_definition"])

        if use_dynamic_so == False:
            self.use_dynamic_so_ttp = CreateToolTip(self.use_dynamic_so_label, LANGUAGES[lang]["use_dynamic_so_no_definition"])
            self.range_cover_label.config(text=LANGUAGES[lang]["range_cover_label"])
            self.range_cover_ttp = CreateToolTip(self.range_cover_label, LANGUAGES[lang]["range_cover_definition"])
        if use_dynamic_so == True:
            self.use_dynamic_so_ttp = CreateToolTip(self.use_dynamic_so_label, LANGUAGES[lang]["use_dynamic_so_yes_definition"])
            self.range_cover_label.config(text=LANGUAGES[lang]["dynamic_so_label"])
            self.range_cover_ttp = CreateToolTip(self.range_cover_label, LANGUAGES[lang]["co_range_cover_definition"])

        # if one == True:
        #     self.one_or_more_ttp = CreateToolTip(self.one_or_more_label, LANGUAGES[lang]["one_or_more_one_long_definition"])
        # else:
        #     self.one_or_more_ttp = CreateToolTip(self.one_or_more_label, LANGUAGES[lang]["one_or_more_more_long_definition"])

        self.martingale_ttp = CreateToolTip(self.martingale_label, LANGUAGES[lang]["martingale_definition"])
        #self.log_distribution_ttp = CreateToolTip(self.log_distribution_label, LANGUAGES[lang]["log_distribution_definition"])
        #self.log_distribution_ttp = CreateToolTip(self.log_coeff_label, LANGUAGES[lang]["log_distribution_definition"])
        self.first_so_coeff_ttp = CreateToolTip(self.first_so_coeff_label, LANGUAGES[lang]["first_so_coeff_definition"])
        self.dynamic_so_coeff_ttp = CreateToolTip(self.dynamic_so_coeff_label, LANGUAGES[lang]["dynamic_so_coeff_definition"])
        self.martingale_ttp = CreateToolTip(self.martingale_label, LANGUAGES[lang]["martingale_definition"])

        self.timeframe_ttp = CreateToolTip(self.timeframe_label, LANGUAGES[lang]["timeframe_definition"])
        self.time_sleep_ttp = CreateToolTip(self.time_sleep_label, LANGUAGES[lang]["time_sleep_definition"])

        self.exit_timeframe_ttp = CreateToolTip(self.exit_timeframe_label, LANGUAGES[lang]["exit_timeframe_definition"])

        self.exit_use_stoch_ttp = CreateToolTip(self.exit_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.exit_stoch_up_level_ttp = CreateToolTip(self.exit_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.exit_cci_level_ttp = CreateToolTip(self.exit_cci_level_label, LANGUAGES[lang]["exit_cci_level_definition"])

        self.exit_rsi_use_stoch_ttp = CreateToolTip(self.exit_rsi_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.exit_rsi_stoch_up_level_ttp = CreateToolTip(self.exit_rsi_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.exit_rsi_level_ttp = CreateToolTip(self.exit_rsi_level_label, LANGUAGES[lang]["exit_rsi_level_definition"])

        self.avg_use_tf_switching_ttp = CreateToolTip(self.avg_use_tf_switching_label, LANGUAGES[lang]["use_tf_switching_definition"])

        self.avg_use_stoch_ttp = CreateToolTip(self.avg_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.avg_stoch_up_level_ttp = CreateToolTip(self.avg_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.avg_cci_level_ttp = CreateToolTip(self.avg_cci_level_label, LANGUAGES[lang]["exit_cci_level_definition"])

        self.avg_rsi_use_stoch_ttp = CreateToolTip(self.avg_rsi_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.avg_rsi_stoch_up_level_ttp = CreateToolTip(self.avg_rsi_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.avg_rsi_level_ttp = CreateToolTip(self.avg_rsi_level_label, LANGUAGES[lang]["exit_rsi_level_definition"])


        self.entry_timeframe_ttp = CreateToolTip(self.entry_timeframe_label, LANGUAGES[lang]["exit_timeframe_definition"])
        self.entry_use_stoch_ttp = CreateToolTip(self.entry_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.entry_stoch_up_level_ttp = CreateToolTip(self.entry_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.entry_cci_level_ttp = CreateToolTip(self.entry_cci_level_label, LANGUAGES[lang]["exit_cci_level_definition"])

        self.entry_rsi_use_stoch_ttp = CreateToolTip(self.entry_rsi_use_stoch_label, LANGUAGES[lang]["exit_use_stoch_definition"])
        self.entry_rsi_stoch_up_level_ttp = CreateToolTip(self.entry_rsi_stoch_up_long_label, LANGUAGES[lang]["exit_stoch_level_definition"])
        self.entry_rsi_level_ttp = CreateToolTip(self.entry_rsi_level_label, LANGUAGES[lang]["exit_rsi_level_definition"])


        self.entry_preset_ttp = CreateToolTip(self.entry_preset_label, LANGUAGES[lang]["preset_definition"])
        self.avg_preset_ttp = CreateToolTip(self.avg_preset_label, LANGUAGES[lang]["preset_definition"])
        self.exit_preset_ttp = CreateToolTip(self.exit_preset_label, LANGUAGES[lang]["preset_definition"])

        self.entry_cci_cross_use_price_ttp = CreateToolTip(self.entry_cci_cross_use_price_label, LANGUAGES[lang]["use_price_definition"])
        self.avg_cci_cross_use_price_ttp = CreateToolTip(self.avg_cci_cross_use_price_label, LANGUAGES[lang]["use_price_definition"])
        self.exit_cci_cross_use_price_ttp = CreateToolTip(self.exit_cci_cross_use_price_label, LANGUAGES[lang]["use_price_definition"])
        #self.exit_use_tv_signals_ttp = CreateToolTip(self.exit_use_tv_signals_label, LANGUAGES[lang]["exit_use_tv_signals_definition"])

        self.time_sleep_ttp = CreateToolTip(self.time_sleep_label, LANGUAGES[lang]["time_sleep_definition"])

        self.global_timeframe_ttp = CreateToolTip(self.global_timeframe_label, LANGUAGES[lang]["global_timeframe_definition"])
        #self.stoch_fastk_period_ttp = CreateToolTip(self.stoch_fastk_period_label, LANGUAGES[lang]["stoch_fastk_period_definition"])
        self.entry_stoch_up_level_ttp = CreateToolTip(self.entry_stoch_up_long_label, LANGUAGES[lang]["stoch_level_definition"])
        #self.ema200_and_delta_label_ttp = CreateToolTip(self.ema200_and_delta_label, LANGUAGES[lang]["ema200_delta_definition"])

        self.profit_ttp = CreateToolTip(self.exit_profit_level_label, LANGUAGES[lang]["profit_definition"])