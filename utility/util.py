import logging
import os
from pathlib import Path

from utility import config


def get_python_files_from_directory(directory: Path,
                                    exclude_dirs: list[str] = None,
                                    ignore_starts_with: tuple = None) -> list[str]:
    """Get a list of string paths to Python files from a directory"""

    if exclude_dirs is None:
        exclude_dirs = []

    exclude_dirs = [Path(directory) / Path(exc_dir) for exc_dir in
                    generate_dir_name_variations(exclude_dirs)]

    python_files = []
    for root, dirs, files in os.walk(directory, topdown=True):

        # Exclude specified directories
        dirs[:] = [d for d in dirs if Path(root) / d not in exclude_dirs and
                   not d.startswith(ignore_starts_with)]

        for file in files:
            if file.endswith(".py"):
                python_file_path = str(Path(root) / file)
                logging.debug(f"Found python file: {python_file_path}")
                python_files.append(python_file_path)

    logging.info(f"Found {len(python_files)} Python files.")

    return python_files


def generate_dir_name_variations(dirs: list[str]) -> list[str]:
    """
    Generate lowercase, uppercase, and capitalized variations for each directory name in dirs.

    Args:
        dirs (List[str]): A list of directory names to generate case variations for.

    Returns:
        List[str]: A list of directory names in all case variations.
    """

    expanded_dirs = []
    for dir_name in dirs:
        expanded_dirs.extend([dir_name.lower(), dir_name.upper(), dir_name.capitalize()])
    return expanded_dirs


def get_repo_owner_from_url(repo_url: str) -> str:
    """Returns the owner of a repository from a git URL"""

    return str(repo_url).rstrip('/').split('/')[-2].strip()


def get_repo_name_from_url_or_path(path_or_url: Path | str) -> str:
    """Returns the name of a repository from either a file path or a URL."""

    if isinstance(path_or_url, Path):
        path_str = str(path_or_url)
    else:
        path_str = path_or_url

    normalized_path = path_str.replace('\\', '/').rstrip('/')
    repo_name = normalized_path.split('/')[-1]
    return repo_name.replace('.git', '')


def get_repository_urls_from_file(file_path: Path) -> list[str]:
    """Get a list of repository URLs from a file"""

    urls = []
    with open(file_path, 'r') as file:
        for line in file:
            urls.append(sanitize_url(line))
    return urls


def absolute_repos_to_relative(absolute_path: str) -> str:
    """Returns the relative path of a repo from an absolute path"""

    return absolute_path.replace(str(config.REPOSITORIES_FOLDER), '').lstrip('/').strip()


def absolute_data_path_to_relative(absolute_path: str) -> str:
    """Returns the relative path of a file from an absolute path"""

    return absolute_path.replace(str(config.DATA_FOLDER), '').lstrip('/').strip()


def get_path_to_repo(repo_url: str) -> Path:
    """Returns the path to a repository based on the URL"""

    name = get_repo_name_from_url_or_path(repo_url)
    return config.REPOSITORIES_FOLDER / name


def sanitize_url(url: str) -> str:
    """Removes any non-printable characters and whitespace"""

    return url.strip().removesuffix('/')


def kb_to_mb_gb(size_in_kb: int) -> str:
    """Convert size from KB to MB or GB if large enough."""

    if size_in_kb < 1024:
        return f"{size_in_kb} KB"
    elif size_in_kb < 1024 * 1024:
        size_in_mb = size_in_kb / 1024
        return f"{size_in_mb:.2f} MB"
    else:
        size_in_gb = size_in_kb / (1024 * 1024)
        return f"{size_in_gb:.2f} GB"


def kb_to_mb(size_in_kb: int) -> float:
    """Convert size from KB to MB."""

    return size_in_kb / 1024


def format_duration(seconds):
    """Formats the duration from seconds to a string in HH:MM:SS format."""

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
