import logging
from pathlib import Path

# Determine the root directory of the project. Assuming `utility` is at the root.
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()
OUTPUT_FOLDER: Path = ROOT_DIR / 'out'
DATA_FOLDER: Path = OUTPUT_FOLDER / 'data'
REPOSITORY_URLS: Path = ROOT_DIR / 'repos.txt'
REPOSITORIES_FOLDER: Path = OUTPUT_FOLDER / 'repositories'
LOGGING_FOLDER: Path = OUTPUT_FOLDER / 'logs'
GRAPHQL_API: str = 'https://api.github.com/graphql'
PYLINT_CONFIG: Path = ROOT_DIR / 'mining' / '.pylintrc'

IGNORE_STARTSWITH: tuple = ('.', '~', '_', '#', '$', '!', '%', '+')
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

DISABLE_PROGRESS_BARS: bool = False
CONSOLE_LOGGING_LEVEL: int = logging.INFO
FILE_LOGGING_LEVEL: int = logging.DEBUG
WRITE_DATABASE: bool = True
WRITE_JSON: bool = True
WRITE_CSV: bool = True
ENABLE_NTFYER: bool = False
