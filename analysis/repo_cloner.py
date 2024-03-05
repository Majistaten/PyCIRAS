import requests
from git import Repo, RemoteProgress, rmtree
from pathlib import Path
import logging
from tqdm import tqdm
from utility import util, config


class CloneProgress(RemoteProgress):
    """Progressbar for the cloning process"""

    def __init__(self, repo_name: str = '', n_cols: any = None, repo_size: str = ''):
        super().__init__()
        self.pbar = tqdm(desc=f'Cloning {repo_name}{f"" if repo_size == "" else f" of size {repo_size}"}',
                         ncols=n_cols,
                         colour="blue",
                         )

    def update(self, op_code, cur_count, max_count=None, message=''):
        if max_count is not None:
            self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()

    def close(self):
        self.pbar.close()


def download_repositories(
        destination_folder: str,
        repo_url_file_path: str = None,
        repo_url_list: list[str] = None) -> list[str] | bool:
    """
    Downloads a list of repositories from a file or a list of URLs.
    Args:
        repo_url_file_path: Path to a file containing a list of repository URLs.
        destination_folder: The folder to clone the repositories to.
        repo_url_list: A list of repository URLs.

    Returns:
        True if all repositories were successfully cloned, else False.
    """
    repository_paths = []
    if repo_url_list is not None:
        repo_urls = repo_url_list
    elif repo_url_file_path is not None:
        url_file = Path(repo_url_file_path)
        if not url_file.is_file():
            logging.error('The provided repository URL file does not exist or is not a file.')
            return False
        repo_urls = util.get_repository_urls_from_file(repo_url_file_path)
    else:
        logging.error('No repository source provided. Please provide either a file or a list of URLs.')
        return False

    logging.info(f'Downloading {len(repo_urls)} repositories.')
    for i, repo_url in enumerate(repo_urls):
        logging.info(f'Downloading repository {i + 1} of {len(repo_urls)}...')
        repository_path = clone_repository(repo_url, destination_folder)
        if repository_path is None:
            logging.error('Failed to download repository from ' + repo_url)
        else:
            repository_paths.append(repository_path)
    logging.info('Finished downloading repositories.')

    return repository_paths


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
            logging.info('Path (' + destination_folder + ') did not exist, creating path.')
            path.mkdir(parents=True, exist_ok=True)

        if (path / repo_name).exists():
            logging.info(f'Repository {repo_name} already exists in {destination_folder}, skipping...')
            return str(path / repo_name)
        repo_size = get_github_repo_size(repo_url)
        logging.info(f'Cloning Git Repository {repo_name} of size {repo_size} from {repo_url} ...')
        Repo.clone_from(repo_url,
                        destination_folder + '/' + repo_name,
                        progress=CloneProgress(repo_name=repo_name, n_cols=150, repo_size=repo_size))

        logging.info(repo_name + ' cloned to ' + destination_folder)
        return destination_folder + '/' + repo_name

    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None


def remove_repositories(content: list[str]) -> None:
    """ Remove all repositories in the content list. """
    logging.info(f'Removing {len(content)} repositories {content}')
    for url in content:
        path = util.get_path_to_repo(url)
        if path.index(config.REPOSITORIES_FOLDER) > -1:
            logging.info(f'Removing: {path}\n')
            rmtree(path)
        else:
            logging.error(f'Something went wrong with the path extraction of {url}, got path {path}')


# TODO: Alternatively move to util?
def get_github_repo_size(url: str) -> str:
    user = url.split('/')[-2]
    repo = url.split('/')[-1]
    api_url = f"https://api.github.com/repos/{user}/{repo}"
    response = requests.get(api_url)
    if response.status_code == 200:
        repo_data = response.json()
        size_in_kb = repo_data['size']
        formatted_size = format_size(size_in_kb)
        logging.info(f"The repository size is: {formatted_size}")
        return formatted_size
    else:
        logging.warning(f"Failed to fetch repository data. Status code: {response.status_code}")
        return ""


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

