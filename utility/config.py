from pathlib import Path

# Determine the root directory of the project. Assuming `utility` is at the root.
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()

OUTPUT_FOLDER: Path = ROOT_DIR / 'out'
DATA_FOLDER: Path = OUTPUT_FOLDER / 'data'
REPOSITORY_URLS: Path = ROOT_DIR / 'repos.txt'
REPOSITORIES_FOLDER: Path = OUTPUT_FOLDER / 'repositories'
GRAPHQL_API: str = 'https://api.github.com/graphql'
DISABLE_PROGRESS_BARS: bool = True
