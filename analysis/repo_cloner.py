from git import Repo, RemoteProgress
from pathlib import Path
import logging
import re
from tqdm import tqdm
from utility import util


class CloneProgress(RemoteProgress):
    """Progressbar for the cloning process"""

    def __init__(self, repo_name: str = '', n_cols: any = None):
        super().__init__()
        self.repo_name = repo_name
        self.pbar = tqdm(desc=f'Cloning {repo_name}', ncols=n_cols, colour="blue")

    def update(self, op_code, cur_count, max_count=None, message=''):
        if max_count is not None:
            self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()

    def close(self):
        self.pbar.close()


def download_repositories(
        destination_folder: str,
        repo_urls_path: str = None,
        repo_url_list: list[str] = None) -> list[str] | bool:
    """
    Downloads a list of repositories from a file or a list of URLs.
    Args:
        repo_urls_path: Path to a file containing a list of repository URLs.
        destination_folder: The folder to clone the repositories to.
        repo_url_list: A list of repository URLs.

    Returns:
        True if all repositories were successfully cloned, else False.
    """
    repository_paths = []
    # TODO: Remove sanitize and use get repo url form util
    if repo_url_list is not None:
        repo_urls = [_sanitize_url(url) for url in repo_url_list]
    elif repo_urls_path is not None:
        url_file = Path(repo_urls_path)
        if not url_file.is_file():
            logging.error('The provided repository URL file does not exist or is not a file.')
            return False
        with open(url_file, 'r') as file:
            repo_urls = [_sanitize_url(line.strip()) for line in file]
    else:
        logging.error('No repository source provided. Please provide either a file or a list of URLs.')
        return False

    logging.info('Downloading repositories...')
    total_repos = len(repo_urls)
    for i, repo_url in enumerate(repo_urls):
        logging.info('Downloading repository ' + str(i + 1) + ' of ' + str(total_repos) + '...')
        repository_path = clone_repository(repo_url, destination_folder)
        if repository_path is None:
            logging.error('Failed to download repository from ' + repo_url)
        else:
            repository_paths.append(repository_path)
    logging.info('Finished downloading repositories.')

    return repository_paths


def _sanitize_url(url: str) -> str:
    """Returns an url without whitespace"""
    return re.sub('[ \n\r\t]', '', url).removesuffix('/')


def clone_repository(repo_url: str, destination_folder: str) -> str | None:
    """
    Clones a Git repository from a given URL to a given destination folder.
    Args:
        repo_url: The URL of the Git repository to clone.
        destination_folder: The folder to clone the repository to.

    Returns:
        True if the repository was successfully cloned, False otherwise.
    """
    try:
        repo_name = util.get_repo_name_from_url(repo_url)
        path = Path(destination_folder)
        if not path.exists() or not path.is_dir():
            logging.warning('Path (' + destination_folder + ') did not exist, creating path.')
            path.mkdir(parents=True, exist_ok=True)

        if (path / repo_name).exists():
            logging.info('Repository ' + repo_name + ' already exists in ' + destination_folder + ', skipping...')
            return str(path / repo_name)

        logging.info('Cloning Git Repository ' + repo_name + ' from ' + repo_url + ' ...')
        Repo.clone_from(repo_url, destination_folder + '/' + repo_name, progress=CloneProgress(repo_name, 150))

        logging.info(repo_name + ' cloned to ' + destination_folder)
        return destination_folder + '/' + repo_name

    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None
