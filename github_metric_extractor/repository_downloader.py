import argparse

from git import Repo, RemoteProgress
from pathlib import Path
import logging
import re
from tqdm import tqdm


class CloneProgress(RemoteProgress):
    def __init__(self, repo_name='', ncols=None):
        super().__init__()
        self.repo_name = repo_name
        self.pbar = tqdm(desc=f'Cloning {repo_name}', ncols=ncols)

    def update(self, op_code, cur_count, max_count=None, message=''):
        if max_count is not None:
            self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()

    def close(self):
        self.pbar.close()


def clone_repository(repo_url, destination_folder):
    """
    Clones a Git repository from a given URL to a given destination folder.
    Args:
        repo_url: The URL of the Git repository to clone.
        destination_folder: The folder to clone the repository to.

    Returns:
        True if the repository was successfully cloned, False otherwise.
    """
    try:
        repo_name = _get_repo_name(repo_url)
        path = Path(destination_folder)
        if not path.exists() or not path.is_dir():
            logging.warning('Path (' + destination_folder + ') did not exist, creating path.')
            path.mkdir(parents=True, exist_ok=True)

        if (path / repo_name).exists():
            logging.info('Repository ' + repo_name + ' already exists in ' + destination_folder + ', skipping...')
            return str(path / repo_name)

        logging.info('Cloning Git Repository ' + repo_name + ' from ' + repo_url + ' ...')
        Repo.clone_from(repo_url, destination_folder + '/' + repo_name, progress=CloneProgress(repo_name, 100))

        logging.info(repo_name + ' cloned to ' + destination_folder)
        return destination_folder + '/' + repo_name
    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None


def download_repositories(repo_url_file=None, destination_folder='./repositories', repo_url_list=None):
    """
    Downloads a list of repositories from a file or a list of URLs.
    Args:
        repo_url_file: Path to a file containing a list of repository URLs.
        destination_folder: The folder to clone the repositories to.
        repo_url_list: A list of repository URLs.

    Returns:
        True if all repositories were successfully cloned, else False.
    """
    repo_urls = []
    repository_paths = []

    if repo_url_list is not None:
        repo_urls = [_sanitize_url(url) for url in repo_url_list]
    elif repo_url_file is not None:
        url_file = Path(repo_url_file)
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


def _sanitize_url(url: str):
    return re.sub('[ \n\r\t]', '', url)


def _get_repo_name(repo_url):
    return repo_url.rstrip('/').split('/')[-1].replace('.git', '')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo-url')
    parser.add_argument('-d', '--destination-folder')
    parser.add_argument('-f', '--url-file')
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)')
    if args.destination_folder is not None:
        if args.repo_url is not None:
            clone_repository(args.repo_url, args.destination_folder)
        if args.url_file is not None:
            download_repositories(repo_url_file=args.url_file, destination_folder=args.destination_folder)

