import logging

def setup_logging(log_path="/var/log/xui-tg-bot.log"):
    logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s - %(message)s")
