from marketmaker.bot import main as boot_bot
from scripts.create_substr import main as create_substr

def main() -> None:
    create_substr()
    boot_bot()