from bot.kernel.config import Config
config = Config("config.toml")
config.load()

APP_NAME = "HF_futures"
APP_VERSION = "1.0.9"
APP_AUTHOR = "Frankie"
APP_WEBSITE = "http://hfbot.site"

APP_MARKET = config.get_value("bot", "market")
APP_EXCHANGE = config.get_value("bot", "exchange")
APP_ALGORITHM = config.get_value("bot", "algorithm")
APP_NOTE = config.get_value("bot", "my_note")