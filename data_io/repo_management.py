import logging
from datetime import datetime
from pathlib import Path

from git import Repo, rmtree
from pydriller import Repository
from rich.progress import Progress

from utility import util
from utility.progress_bars import GitProgress, IterableProgressWrapper


def clone_repos(repo_directory: Path, repo_urls: list[str], progress: Progress) -> list[Path]:
    """
    Clones repositories from a list of URLs, and returns the paths.
    Args:
        repo_directory: The folder to clone the repositories to.
        repo_urls: A list of repository URLs.

    Returns:
        A list of repository paths.
    """

    repo_paths = []
    for repo_url in IterableProgressWrapper(repo_urls,  # TODO disable if multiprocessing or config is off
                                            progress,
                                            description="Cloning Repositories",
                                            postfix="Repos"):

        path = _clone_repo(repo_directory, repo_url, progress)

        if path is None:
            logging.error(f'Failed to download repository from {repo_url}')
        else:
            repo_paths.append(path)

    return repo_paths


def _clone_repo(repos_directory: Path, repo_url: str, progress: Progress) -> Path | None:
    """
    Clones a Git repository from a given URL to a given destination folder.
    Args:
        repo_url: The URL of the Git repository to clone.
        repos_directory: The folder where repos are stored.
    Returns:
        The repository path.
    """
    try:
        repo_name = util.get_repo_name_from_url_or_path(repo_url)

        if not repos_directory.exists() or not repos_directory.is_dir():
            logging.info(f'{repos_directory} did not exist, creating it.')
            repos_directory.mkdir(parents=True, exist_ok=True)

        repo_path = repos_directory / repo_name

        if repo_path.exists():
            logging.info(f'{repo_name} already exists in {repos_directory}, skipping clone')
            return repo_path

        logging.info(f'Cloning Git Repository {repo_name} from {repo_url} to {repo_path}')

        Repo.clone_from(repo_url,
                        repo_path,
                        progress=GitProgress(progress, description=repo_name))

        logging.info(f'Finished cloning {repo_name}')

        return repo_path

    except Exception as ex:
        logging.error('Something went wrong when cloning the repository!\n' + str(ex))
        return None


# TODO: Baka in i pipeline och skriv ut i fil.
def get_repo_paths_and_commit_metadata(repos_directory: Path,
                                       repo_paths: list[Path]) -> dict[str, list[tuple[str, datetime]]]:
    """Get a dict of repo paths with a list of tuples containing commit hashes and dates"""
    repos: dict[str, Repository] = load_repos(repos_directory, repo_paths)
    repos_with_commit_hashes_and_dates = {}
    for repo_path, repo in repos.items():
        hashes_and_dates = []
        for commit in repo.traverse_commits():
            hashes_and_dates.append((commit.hash, commit.committer_date))

        repos_with_commit_hashes_and_dates[repo_path] = hashes_and_dates

    return repos_with_commit_hashes_and_dates


def load_repos(repos_directory: Path, repos: list[Path | str]) -> (dict[str, Repository]):
    """Load repos for mining, from an URL or a path."""

    repos_directory.mkdir(parents=True, exist_ok=True)
    logging.debug(f'Loading repositories {repos} from {repos_directory}')

    return {
        str(repo_path_or_url):
            _load_repo(repos_directory, repo_path_or_url) for repo_path_or_url in repos
    }


def _load_repo(repos_directory: Path, url_or_path: str) -> Repository:
    """Load repository stored locally, or clone and load if not present"""

    repo_name = util.get_repo_name_from_url_or_path(url_or_path)
    repo_path = repos_directory / repo_name

    if repo_path.exists():
        logging.info(f'Loading {util.get_repo_name_from_url_or_path(url_or_path)} from disk')
        return Repository(str(repo_path), num_workers=1)
    else:
        logging.info(f'Cloning and loading {util.get_repo_name_from_url_or_path(url_or_path)}')
        return Repository(url_or_path, clone_repo_to=str(repos_directory), num_workers=1)


def remove_repos(repo_urls: list[str]) -> None:
    """Remove a list of repositories."""

    logging.info(f'Removing {len(repo_urls)} repositories {repo_urls}')

    for url in repo_urls:
        path = util.get_path_to_repo(url)
        if path.exists():
            logging.info(f'Removing: {path}')

            rmtree(path)
            if path.exists():
                logging.error(f'Failed to remove {path}')

        else:
            logging.debug(f'Could not find repository path. Will not try to remove non-existing repositories.')
