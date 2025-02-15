# Marketmaker Bot

## Setup

1. Ensure Python is installed.
2. Create a virtual environment. The most common way to do this is with `python -m venv venv`
3. Activate the virtual environment, e.g. with `.\venv\Scripts\activate` on PowerShell or `source ./venv/bin/activate` on Ubuntu
4. Install the bot and its dependenceis with `pip install -e .`

The `-e` denotes an EDITABLE install, meaning you can change the code and run the bot again, without needing to reinstall.

**If you add dependencies to the project, please update `pyproject.toml` and re-run step 4.**

## Configuration

Create a file called `.env` with the following format:

```plaintext
BOT_TOKEN=... # discord bot token
PROB=... # percentage probability of puzzle spawning on msg
DEV_MODE=... # 1 for dev, 0 for prod
TIMED_SPAWN=... # 1 for having puzzles spawn on a 1 to 10 min timer, 0 for no timed puzzles
CHANNEL=... # discord channel id of the channel bot should default announcements to (ex taxation announcements)
NORMAL_MIN_WORDS=... # minimum number of words you'd like to be possible for each substring in a normal puzzle (ex 250)
HARD_MIN_WORDS=... # minimum number of words you'd like to be possible for each substring in a hard puzzle (ex 100)
AUTHOR=... # discord user id of the bot's author (may not be necessary)
```

## Running the Bot

1. Ensure the virtual environment is activated.
2. Run `bot`

## Project Layout

* `marketmaker`: source files for bot
* `scripts`: "one-time" run files for generating e.g. static word lists
* `static`: static data
