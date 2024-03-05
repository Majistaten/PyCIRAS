from pathlib import Path

#TODO paths returneras som Path objekt istället för strängar, fixa i resten av appen

# Determine the root directory of the project. Assuming `utility` is at the root.
ROOT_DIR = Path(__file__).parent.parent.resolve()

OUTPUT_FOLDER = ROOT_DIR / 'out'
DATA_FOLDER = OUTPUT_FOLDER / 'data'
REPOSITORY_URLS = ROOT_DIR / 'repos.txt'
REPOSITORIES_FOLDER = OUTPUT_FOLDER / 'repositories'
GRAPHQL_API = 'https://api.github.com/graphql'

