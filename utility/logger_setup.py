import logging
from datetime import datetime
from rich.logging import RichHandler
from rich.console import Console
from utility import config
from pathlib import Path

LOG_DIR = Path(config.LOGGING_FOLDER)
LOG_FILE = datetime.now().strftime('%Y-%m-%d_%H-%M.log')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# TODO få ut pydriller och pylint logs på debug nivå in i loggen
def setup_root_logger():
    """Configure the root logger with custom handlers."""
    if not logging.root.handlers:
        console = Console()

        file_handler = logging.FileHandler(LOG_DIR / LOG_FILE, mode='a', encoding='utf-8')
        file_handler.setLevel(config.FILE_LOGGING_LEVEL)

        rich_handler = RichHandler(console=console, rich_tracebacks=True)
        rich_handler.setLevel(config.CONSOLE_LOGGING_LEVEL)

        console_format = "%(message)s"
        console_formatter = logging.Formatter(console_format)
        rich_handler.setFormatter(console_formatter)

        logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, rich_handler])

# TODO försök komma åt pylints logger        logging.getLogger('pylint').setLevel(logging.INFO)

        logging.getLogger('pydriller.repository').setLevel(logging.WARNING)

        return console


def get_logger(name=None):
    """Configure and return a custom or the root logger."""
    rich_console = setup_root_logger()
    return logging.getLogger(name), rich_console
