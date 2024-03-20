from git import Repo, RemoteProgress, rmtree
from utility.progress_bars import CloneProgress
import logging
from datetime import datetime
from pydriller import Repository
from utility import util, config, ntfyer
import requests
from git import Repo, RemoteProgress, rmtree
from pathlib import Path
import logging
from utility import util, config
from utility.progress_bars import CloneProgress


def prepare_repositories(destination_folder: Path, repo_urls: list[str]) -> list[Path]:
    """
    Prepares a list of repositories from a list of URLs.
    Args:
        destination_folder: The folder to clone the repositories to or search for its existence.
        repo_urls: A list of repository URLs.

    Returns:
        A list of repository paths.
    """
    repository_paths = []
    logging.info(f'Downloading {len(repo_urls)} repositories.')
    for i, repo_url in enumerate(repo_urls):
        logging.info(f'Downloading repository {i + 1} of {len(repo_urls)}...')
        repository_path = prepare_repository(repo_url, destination_folder, postfix=f"({i + 1}/{len(repo_urls)})")
        if repository_path is None:
            logging.error(f'Failed to download repository from {repo_url}')
        else:
            repository_paths.append(repository_path)
    logging.info('Finished downloading repositories.')

    return repository_paths


def prepare_repository(repo_url: str, destination_folder: Path, postfix: str = "") -> Path | None:
    """
    Clones a Git repository from a given URL to a given destination folder.
    Args:
        repo_url: The URL of the Git repository to clone.
        destination_folder: The folder to clone the repository to.
        postfix: A postfix to add to the progress bar.

    Returns:
        The repository path.
    """
    try:
        repo_name = util.get_repo_name_from_url_or_path(repo_url)
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
                        progress=CloneProgress(description=repo_name, postfix=postfix,
                                               disable=config.DISABLE_PROGRESS_BARS))

        logging.info(f'Finished cloning {repo_path}')
        return repo_path

    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None


# TODO: Baka in i pipeline och skriv ut i fil.
def get_repo_paths_and_commit_metadata(repos_directory: Path,
                                       repo_paths: list[Path]) -> dict[str, list[tuple[str, datetime]]]:
    """Get a dict of repo paths with a list of tuples containing commit hashes and dates"""
    repos: dict[str, Repository] = load_repositories(repos_directory, repo_paths)
    repos_with_commit_hashes_and_dates = {}
    for repo_path, repo in repos.items():
        hashes_and_dates = []
        for commit in repo.traverse_commits():
            hashes_and_dates.append((commit.hash, commit.committer_date))

        repos_with_commit_hashes_and_dates[repo_path] = hashes_and_dates

    return repos_with_commit_hashes_and_dates


def load_repositories(repo_directory: Path, repos: list[Path | str]) -> (dict[str, Repository]):
    """Load repos for mining, from an URL or a path."""

    repo_directory.mkdir(parents=True, exist_ok=True)
    logging.info('Loading repositories.')

    return {
        str(repo_path_or_url):
            _load_repository(repo_path_or_url, repo_directory) for repo_path_or_url in repos
    }


def _load_repository(url_or_path: str, repo_directory: Path) -> Repository:
    """Load repository stored locally, or clone and load if not present"""

    repo_name = util.get_repo_name_from_url_or_path(url_or_path)
    repo_path = repo_directory / repo_name

    if repo_path.exists():
        return Repository(str(repo_path))
    else:
        return Repository(url_or_path, clone_repo_to=str(repo_directory))


def remove_repos(content: list[str]) -> None:
    """ Remove all repositories in the content list. """
    logging.info(f'Removing {len(content)} repositories {content}')
    for url in content:
        path = util.get_path_to_repo(url)
        if path.exists():
            logging.info(f'Removing: {path}\n')
            rmtree(path)
            if path.exists():
                logging.error(f'Failed to remove {path}')
        else:
            logging.info(f'Could not find repository path. Will not try to remove non-existing repositories.')


def get_github_repo_size(url: str) -> str:
    user = util.get_repo_owner_from_url(url)
    repo = util.get_repo_name_from_url_or_path(url)
    api_url = f"https://api.github.com/repos/{user}/{repo}"
    response = requests.get(api_url)
    if response.status_code == 200:
        repo_data = response.json()
        size_in_kb = repo_data['size']
        formatted_size = util.format_size(size_in_kb)
        return formatted_size
    else:
        logging.warning(f"Failed to fetch repository data from {api_url}. Status code: {response.status_code}")
        return ""
