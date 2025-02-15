# Marketmaker Bot

## Setup

1. Ensure Python is installed.
2. Create a virtual environment. The most common way to do this is with `python -m venv venv`
3. Activate the virtual environment, e.g. with `.\venv\Scripts\activate`
4. Install the bot and its dependenceis with `pip install -e .`

The `-e` denotes an EDITABLE install, meaning you can change the code and run the bot again, without needing to reinstall.

**If you add dependencies to the project, please update `pyproject.toml` and re-run step 4.**

## Configuration

Create a file called `.env` with the following format:

```plaintext
BOT_TOKEN=...
PROB=...
DEV_MODE=...
```

## Running the Bot

1. Ensure the virtual environment is activated.
2. Run `bot`

## Project Layout

* `marketmaker`: source files for bot
* `scripts`: "one-time" run files for generating e.g. static word lists
* `static`: static data
