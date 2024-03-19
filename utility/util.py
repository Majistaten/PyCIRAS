import os
import logging
from pathlib import Path
from utility import config


def get_python_files_from_directory(directory: Path) -> list[str]:
    """Get a list of string paths to Python files from a directory"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                logging.info(f"Found python file: {str(os.path.join(root, file))}")
                python_files.append(str(os.path.join(root, file)))
    logging.info(f"Found {len(python_files)} python files in {directory}")
    return python_files


def get_repo_name_from_url(repo_url: str) -> str:
    """Returns the name of a repository from a git URL"""
    return str(repo_url).rstrip('/').split('/')[-1].replace('.git', '').strip()


def get_repo_owner_from_url(repo_url: str) -> str:
    """Returns the owner of a repository from a git URL"""
    return str(repo_url).rstrip('/').split('/')[-2].strip()


def get_repo_name_from_path(path: str) -> str:
    """Returns the name of a repository from a path"""
    return path.replace('\\', '/').rstrip('/').split('/')[-1].strip()


def get_repository_urls_from_file(file_path: Path) -> list[str]:
    """Get a list of repository URLs from a file"""
    urls = []
    logging.info(f"Getting repository urls from file: {file_path}")
    with open(file_path, 'r') as file:
        for line in file:
            urls.append(sanitize_url(line))
    return urls


def get_file_relative_path_from_absolute_path(absolute_path: str) -> str:
    """Returns the relative path of a file from an absolute path"""
    return absolute_path.replace(str(config.REPOSITORIES_FOLDER), '').lstrip('/').strip()


def get_path_to_repo(repo_url: str) -> Path:
    name = get_repo_name_from_url(repo_url)
    return config.REPOSITORIES_FOLDER / name


def sanitize_url(url: str) -> str:
    """Removes any non-printable characters and whitespace"""
    return url.strip().removesuffix('/')


def format_size(size_in_kb: int) -> str:
    """Convert size from KB to MB or GB if large enough."""
    if size_in_kb < 1024:
        return f"{size_in_kb} KB"
    elif size_in_kb < 1024 * 1024:
        size_in_mb = size_in_kb / 1024
        return f"{size_in_mb:.2f} MB"
    else:
        size_in_gb = size_in_kb / (1024 * 1024)
        return f"{size_in_gb:.2f} GB"


def format_duration(seconds):
    """Formats the duration from seconds to a string in HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

