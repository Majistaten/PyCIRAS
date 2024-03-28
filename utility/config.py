import logging
from pathlib import Path

# Determine the root directory of the project. Assuming `utility` is at the root.
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()
# Define the output folder for the mined data, logs and repositories.
OUTPUT_FOLDER: Path = ROOT_DIR / 'out'
# Define the output folders for the mined data.
DATA_FOLDER: Path = OUTPUT_FOLDER / 'data'
# Define the path to a file containing URLs of repositories to mine.
REPOSITORY_URLS: Path = ROOT_DIR / 'repos.txt'
# Define the repository folder where the repositories will be searched for, or cloned to.
REPOSITORIES_FOLDER: Path = OUTPUT_FOLDER / 'repositories'
# Define the folder where the logs will be stored.
LOGGING_FOLDER: Path = OUTPUT_FOLDER / 'logs'
# Define the URL to the GitHub GraphQL API. If used, ensure to provide a valid token in the .env file.
GRAPHQL_API: str = 'https://api.github.com/graphql'
# Define the path to the .pylintrc file, containing the Pylint configuration.
PYLINT_CONFIG: Path = ROOT_DIR / 'mining' / '.pylintrc'

# This is where you specify prefixes for directories that you want to ignore when mining data.
IGNORE_STARTSWITH: tuple = ('.', '~', '_', '#', '$', '!', '%', '+')
# This is where you specify directories that you want to ignore when mining data.
IGNORE_DIRECTORIES: list[str] = [
    # Common virtual environments
    'env', 'venv', 'env.bak', 'venv.bak',

    # Version control
    'vcs',

    # Dependency directories
    'node_modules', 'bower_components',

    # Build/output directories
    'build', 'dist', 'lib', 'lib64', 'bin', 'wheelhouse', 'wheels',
    'develop-eggs', 'eggs', 'parts', 'sdist', 'var', 'share',

    # Temporary/Backup files
    'temp', 'tmp',

    # Logs and data
    'logs', 'data', 'dataset', 'datasets',

    # Documentation
    'docs', 'notes', 'wiki', 'documentation',

    # Cache
    'cache', 'target',

    # Specific tool/framework directories
    'migrations', 'assets', 'static', 'media', 'vendor', 'third_party',
    'instance',  # Flask-specific directory

    # Configuration and settings
    'config', 'settings', 'ini', 'manifest',

    # Development environment
    'vagrant', 'docker', 'dockerfiles', 'vagrantfiles',

    # IPython
    'profile_default',

    # Miscellaneous
    'downloads',  # Often used for downloaded dependencies or data
    'cython_debug',  # Cython debug symbols
    'site'  # Python site-packages directory, sometimes used in a local context
]

# Disables the console progress bars if set to true.
DISABLE_PROGRESS_BARS: bool = False
# Specify the level of logging for the console.
CONSOLE_LOGGING_LEVEL: int = logging.WARNING
# Specify the level of logging for the log files.
FILE_LOGGING_LEVEL: int = logging.DEBUG
# If set to true, the collected raw data will be inserted into a database.
WRITE_DATABASE: bool = True
# If set to true, the collected raw data will be written to a JSON file.
WRITE_JSON: bool = False
# If set to true, the collected data will be parsed and written to a CSV file.
WRITE_CSV: bool = True
# If set to true, a notification will be sent when the process is complete using ntfyer. This requires valid credentials added to the .env file.
ENABLE_NTFYER: bool = True
