from pathlib import Path
import logging

# Determine the root directory of the project. Assuming `utility` is at the root.
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()

OUTPUT_FOLDER: Path = ROOT_DIR / 'out'
DATA_FOLDER: Path = OUTPUT_FOLDER / 'data'
REPOSITORY_URLS: Path = ROOT_DIR / 'repos.txt'
REPOSITORIES_FOLDER: Path = OUTPUT_FOLDER / 'repositories'
GRAPHQL_API: str = 'https://api.github.com/graphql'
LOGGING_FOLDER: Path = OUTPUT_FOLDER / 'logs'
DISABLE_PROGRESS_BARS: bool = False
VERBOSE_LOGGING_LEVEL: int = logging.WARNING
FILE_LOGGING_LEVEL: int = logging.DEBUG
ENABLE_NTFYER: bool = False

