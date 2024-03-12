import requests
from git import Repo, RemoteProgress, rmtree
from pathlib import Path
import logging
from utility import util, config
from utility.progress_bars import CloneProgress


def download_repositories(
        destination_folder: Path,
        repo_urls_file_path: Path = None,
        repo_urls_list: list[str] = None) -> list[Path] | bool:
    """
    Downloads a list of repositories from a file or a list of URLs.
    Args:
        repo_urls_file_path: Path to a file containing a list of repository URLs.
        destination_folder: The folder to clone the repositories to.
        repo_urls_list: A list of repository URLs.

    Returns:
        True if all repositories were successfully cloned, else False.
    """
    repository_paths = []
    if repo_urls_list is not None:
        repo_urls = repo_urls_list
    elif repo_urls_file_path.exists() and repo_urls_file_path.is_file():
        repo_urls = util.get_repository_urls_from_file(repo_urls_file_path)
    else:
        logging.error('No repository source provided. Please provide either a file or a list of URLs.')
        return False

    logging.info(f'Downloading {len(repo_urls)} repositories.')
    for i, repo_url in enumerate(repo_urls):
        logging.info(f'Downloading repository {i + 1} of {len(repo_urls)}...')
        repository_path = clone_repository(repo_url, destination_folder, postfix=f"({i + 1}/{len(repo_urls)})")
        if repository_path is None:
            logging.error(f'Failed to download repository from {repo_url}')
        else:
            repository_paths.append(repository_path)
    logging.info('Finished downloading repositories.')

    return repository_paths


def clone_repository(repo_url: str, destination_folder: Path, postfix: str = "") -> Path | None:
    """
    Clones a Git repository from a given URL to a given destination folder.
    Args:
        repo_url: The URL of the Git repository to clone.
        destination_folder: The folder to clone the repository to.
        postfix: A postfix to add to the progress bar.

    Returns:
        True if the repository was successfully cloned, False otherwise.
    """
    try:
        repo_name = util.get_repo_name_from_url(repo_url)
        if not destination_folder.exists() or not destination_folder.is_dir():
            logging.info(f'Path {destination_folder} did not exist, creating path.')
            destination_folder.mkdir(parents=True, exist_ok=True)
        repo_path = destination_folder / repo_name
        if repo_path.exists():
            logging.info(f'Repository {repo_name} already exists in {destination_folder}, skipping...')
            return repo_path
        repo_size = get_github_repo_size(repo_url)
        logging.info(f'Cloning Git Repository {repo_name} of size {repo_size} from {repo_url} ...')
        Repo.clone_from(repo_url,
                        repo_path,
                        progress=CloneProgress(description=repo_name, postfix=postfix, disable=config.DISABLE_PROGRESS_BARS))

        logging.info(f'Finished cloning {repo_path}')
        return repo_path

    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None


def remove_repositories(content: list[str]) -> None:
    """ Remove all repositories in the content list. """
    logging.info(f'Removing {len(content)} repositories {content}')
    for url in content:
        path = util.get_path_to_repo(url)
        logging.info(f'Removing: {path}\n')
        rmtree(path)
        if path.exists():
            logging.error(f'Failed to remove {path}')


# TODO: Alternatively move to util?
def get_github_repo_size(url: str) -> str:
    user = url.split('/')[-2]
    repo = url.split('/')[-1]
    api_url = f"https://api.github.com/repos/{user}/{repo}"
    response = requests.get(api_url)
    if response.status_code == 200:
        repo_data = response.json()
        size_in_kb = repo_data['size']
        formatted_size = util.format_size(size_in_kb)
        return formatted_size
    else:
        logging.warning(f"Failed to fetch repository data. Status code: {response.status_code}")
        return ""

