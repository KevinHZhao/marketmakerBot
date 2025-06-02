from .crossword import Crossword
from .economy import Economy
from .fun import Fun
from .leaderboard import Leaderboard
from .puzzle import Puzzle
from .influxdb_queries import InfluxDBQueries

cogs = [Economy, Fun, Puzzle, Leaderboard, Crossword, InfluxDBQueries]