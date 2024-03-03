import os
import logging

from utility import config


def get_python_files_from_directory(directory: str) -> list[str]:
    """Get a list of string paths to Python files from a directory"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                logging.info(f"Found python file: {str(os.path.join(root, file))}")
                python_files.append(str(os.path.join(root, file)))
    return python_files


def get_repo_name_from_url(repo_url: str) -> str:
    """Returns the name of a repository from a git URL"""
    return str(repo_url).rstrip('/').split('/')[-1].replace('.git', '').strip()


def get_repo_name_from_path(path: str) -> str:
    """Returns the name of a repository from a path"""
    return str(path).replace('\\', '/').rstrip('/').split('/')[-1].strip()


def get_repository_urls_from_file(file_path: str) -> list[str]:
    """Get a list of repository URLs from a file"""
    urls = []
    with open(file_path, 'r') as file:
        for line in file:
            urls.append(sanitize_url(line))
    return urls


def get_path_to_repo(repo_url: str) -> str:
    name = get_repo_name_from_url(repo_url)
    return config.REPOSITORIES_FOLDER + name


def sanitize_url(url: str) -> str:
    """Removes any non-printable characters and whitespace"""
    return url.strip().removesuffix('/')

