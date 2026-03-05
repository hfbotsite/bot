#!/usr/bin/env python3

import sys
import os
import psutil
import re
import time
import signal
import threading

from typing import List
import tkinter as tk
from tkinter import ttk, Text, messagebox
import pytoml as toml

from bot.kernel import Logger
from bot.kernel import StoppableThread
from bot.defines import APP_NAME, APP_VERSION, LOGGING_DEBUG_PATH, LOGGING_OUTPUT_PATH, LANGUAGES

from bot.run import run
from bot.test import test

import asyncio

from bot.kernel import Config
config = Config("config.toml")
config.load()

LANG = config.get_value("bot", "language")
write_to_file = config.get_value("logging", "write_to_file")
#ALGORITHM = config.get_value("bot", "algorithm")

logger = Logger(LOGGING_DEBUG_PATH, write_to_file).get_logger()
logger.info("Start %s..." % APP_NAME)

def clear_db():
    db = "bot.db"

    def log(*args):
        logger.info(" ".join([str(x) for x in args]))

    try:
        f = open(LOGGING_DEBUG_PATH, 'w')
        log("-----------------")
        log("Log-file: The log-file was successfully cleared")
    except IOError:
        log("Log-file: An IOError has occurred!")
    finally:
        f.close()

    if os.path.isfile(db):
        os.remove(db)
        log("DB-file: The database was successfully deleted")

    else:
        log("DB-file: %s file not found" % db)


#def add_avr():
    #db = "bot.db"

def close_app(app_name):
    running_apps = psutil.process_iter(['pid', 'name'])  # returns names of running processes
    found = False
    for app in running_apps:
        sys_app = app.info.get('name').split('.')[0].lower()

        if sys_app in app_name.split() or app_name in sys_app:
            pid = app.info.get('pid')  # returns PID of the given app if found running

            try:  # deleting the app if asked app is running.(It raises error for some windows apps)
                app_pid = psutil.Process(pid)
                app_pid.terminate()
                found = True
            except:
                pass

        else:
            pass
    if not found:
        print(app_name + " not found running")
    else:
        print(app_name + '(' + sys_app + ')' + ' closed')

def exit_handler(signum, frame):
    logger.info("Exit. <Ctrl+C>")

    sys.exit()

def run_task(func, args):
    th = StoppableThread()
    th.run(target=func, args=(th, *args), daemon=True)
    return th

def main(sysargv: List[str]) -> None:
    logger.info("start@thread(%s)" % threading.get_ident())
    signal.signal(signal.SIGINT, exit_handler)

    from bot.kernel import Gui
    root = tk.Tk()

    gui = Gui(master=root)
    gui.configure(config)
    gui.build()
    # Configure logging
    from bot.middlewares import LoggingMiddleware
    logging_middleware = LoggingMiddleware(gui=gui)
    task_logger = Logger(LOGGING_OUTPUT_PATH, write_to_file).get_logger()
    task_logger.addHandler(logging_middleware)
    task_elements = []

    state = {
      "fixed_profit": False,
      "selected_coin": tk.StringVar(),
      "manual_averaging": tk.BooleanVar(),
      "manual_sell": tk.BooleanVar(),
      "needed_stop": False,
      "send_needed_stop": tk.BooleanVar(),
      "needed_stop_with_take_profit": tk.BooleanVar(),
      "task_elements": []
    }
    def shutdown(loop):
        #loop = asyncio.get_running_loop()
        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.stop()
        loop.close()
        sys.exit(1)

    def observable_stop_events(self_th, th, loop):
        while not self_th.stopped():
            time.sleep(0.01)
            if state["needed_stop_with_take_profit"].get():
                #while state["needed_stop_with_take_profit"].get():
                while state["needed_stop"] == False and state["needed_stop_with_take_profit"].get():
                    time.sleep(0.01)
                    if state["fixed_profit"]:
                        break

            if state["needed_stop"] or state["send_needed_stop"].get() or (state["needed_stop_with_take_profit"].get() and state["fixed_profit"]):
                task_logger.info("Stopping thread...")
                task_logger.disabled = True

                th.stop()


                logger.info("stop@thread(%s)" % th.get_ident())
                gui.switch_behaviour(runned=False)

                for b in state["task_elements"]:
                    b.destroy()
                state["task_elements"].clear()
                state["needed_stop"] = False
                state["send_needed_stop"].set(False)
                state["fixed_profit"] = False
                state["manual_averaging"].set(False)
                state["manual_sell"].set(False)
                state["needed_stop_with_take_profit"].set(False)
                self_th.stop()



    def log(*args):
        logger.info(" ".join([str(x) for x in args]))

    def stop_task(th):
        state["needed_stop"] = True
        state["send_needed_stop"].set(True)
        #close_app('ticks_generator')
        #time.sleep(0.1)
        #subprocess.call("TASKKILL /F /IM ticks_generator.exe", shell=True)

    def averaging_task(th):
        MsgBox = tk.messagebox.askquestion('Manual averaging', 'Are you sure you want to average your position?',
                                           icon='warning')
        if MsgBox == 'yes':
            state["manual_averaging"].set(True)
            log("MANUAL AVERAGING button pressed")

        else:
            tk.messagebox.showinfo('Return', 'You will now return to the application screen')
            #root.destroy()
        #print("Pressed")

    def sell_task(th):
        if gui.algorithm.get() == 'long':
            MsgBox = tk.messagebox.askquestion('Sell task', 'Are you sure you want to sell previously bought coins?', icon='warning')
        else:
            MsgBox = tk.messagebox.askquestion('Buy task', 'Are you sure you want to buy back the sold coins?', icon='warning')

        if MsgBox == 'yes':
            state["manual_sell"].set(True)
            log("MANUAL SELL/BUY button pressed")

        else:
            tk.messagebox.showinfo('Return', 'You will now return to the application screen')
            #root.destroy()
        #print("Pressed")

    def run_task_run():
        #BASE_COIN = config.get_value("bot", "base_coin")
        #coins = BASE_COIN.replace(' ', '').split(',')
        loop = asyncio.new_event_loop()
        task_logger.disabled = False
        th = run_task(run, (config, task_logger, state, loop))
        logger.info("start@thread(%s)" % th.get_ident())
        gui.switch_behaviour(runned=True)
        gui.purge_logs()
        run_task(observable_stop_events, args=(th, loop))
        state["task_elements"].append(gui.create_button(text=LANGUAGES[LANG]["button_stop"], width=10, padx=7, command=lambda: stop_task(th)))
        state["task_elements"].append(gui.create_menu_to_select_coin(variable=state["selected_coin"]))
        state["task_elements"].append(gui.create_checkbox(text=LANGUAGES[LANG]["button_take_profit"], variable=state["needed_stop_with_take_profit"]))
        state["task_elements"].append(gui.create_button(text=LANGUAGES[LANG]["button_manual_avg"], width=18, padx=10, command=lambda: averaging_task(th)))
        state["task_elements"].append(gui.create_button(text=LANGUAGES[LANG]["fix_manually"], width=18, padx=10, command=lambda: sell_task(th)))


    def run_task_test():
        loop = asyncio.new_event_loop()
        task_logger.disabled = False
        th = run_task(test, (config, task_logger, loop))
        logger.info("start@thread(%s)" % th.get_ident())
        gui.switch_behaviour(runned=True)
        gui.purge_logs()
        run_task(observable_stop_events, args=(th, loop))
        gui.create_button(side=tk.LEFT, removeOnClick=True, text=LANGUAGES[LANG]["button_back_to_settings"], width=12, padx=7, command=lambda: stop_task(th))

    gui.create_button(text=LANGUAGES[LANG]["button_run"], width=10, padx=7, command=lambda: run_task_run())
    gui.create_button(text=LANGUAGES[LANG]["button_test"], width=10, padx=7, command=lambda: run_task_test())
    #gui.create_button(text="Clear the database", width=20, padx=7, command=clear_db)

    # Mainloop
    gui.mainloop()

if __name__ == '__main__':
    main(sys.argv[1:])
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main(sys.argv[1:]))
