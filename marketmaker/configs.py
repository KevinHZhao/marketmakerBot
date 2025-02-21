import os

from dotenv import load_dotenv

load_dotenv(override = True)

# Setup configs
prob_coin_env = os.getenv("PROB")
if prob_coin_env is None:
    raise Exception("No PROB provided in .env file.")
prob_coin = int(prob_coin_env)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    raise Exception("No BOT_TOKEN provided in .env file.")

normal_min_env = os.getenv("NORMAL_MIN_WORDS")
if normal_min_env is None:
    raise Exception("No NORMAL_MIN_WORDS provided in .env file.")
normal_min_words = int(normal_min_env)

hard_min_env = os.getenv("HARD_MIN_WORDS")
if hard_min_env is None:
    raise Exception("No HARD_MIN_WORDS provided in .env file.")
hard_min_words = int(hard_min_env)

time_env = os.getenv("TIMED_SPAWN")
if time_env is None:
    raise Exception("No TIMED_SPAWN provided in .env file.")
timed = bool(int(time_env))

channelid = os.getenv("CHANNEL")
if channelid is None:
    raise Exception("No CHANNEL provided in .env file.")

dev_mode_env = os.getenv("DEV_MODE")
if dev_mode_env is None:
    raise Exception("No DEV_MODE provided in .env file.")
dev = bool(int(dev_mode_env))
