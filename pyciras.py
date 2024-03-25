"""This module provides the main entry point for the PyCIRAS application and the main mining functionality."""

# TODO Skriv docs på allt, inklusive moduler, parametrar, typer, och README
# TODO linta, döp om saker, refaktorera allmänt
# TODO gå igenom linter issues och fixa allt
# TODO insertera log statements på alla olika execution branches på info-nivå
# TODO kolla .pylintrc settings så man får ut alla andra intressanta metrics
# TODO progressbar stannar om det kastas error för ett syntax error i en fil under unit testing analysis
# TODO error handling här i denna filen?
# TODO fixa bättre docstrings som förklarar parametrar
# TODO Sätt ut logging.info överallt, se över så det är samma format överallt
# TODO kolla igenom git mining så vi får med exakt alla metrics vi vill ha
# TODO flytta datamappen utanför projekt-directory
# TODO mina och skriv per commit istället för per repo, mindre minnesanvändning
# TODO byt ut alla any type annotations till Any
# TODO specifiera en config option för att sätta workers till både pylint och pydriller
# TODO läs koden och dokumentation till Pydriller och Pylint och kolla alla options

# TODO testa progressbars i Jupyter, advance/update? refresh=true?

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import rich.traceback
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from data_io import data_management, repo_management
from mining import git_mining, lint_mining, test_mining
from utility import config, logger_setup, ntfyer, util
from utility.progress_bars import IterableColumn
from utility.timer import timed

rich.traceback.install()
data_directory = data_management.make_data_directory()
logger, rich_console = logger_setup.get_logger('pyciras_logger')
progress = Progress(
    SpinnerColumn(),
    TextColumn('[bold blue]{task.description}', justify='right'),
    BarColumn(bar_width=None),
    IterableColumn(),
    TaskProgressColumn(),
    TimeRemainingColumn(),
    TimeElapsedColumn(),
    console=rich_console,
    disable=util.config.DISABLE_PROGRESS_BARS
)


def run_repo_cloner(repo_urls: list[str] = None,
                    chunk_size: int = 1,
                    multiprocessing: bool = False):
    """
    Clones a set of repositories specified by a list of URLs or from a predefined file if no list is
    provided.

    This function facilitates the cloning of multiple repositories in chunks, optionally using multiprocessing for
    improved efficiency. The operation's progress and duration are logged, and a notification is sent upon completion.

    Parameters:
        repo_urls (list[str], optional): List of repository URLs to clone. If None, the list is loaded from a file.
        chunk_size (int, optional): Number of repositories to clone in each operation chunk. Defaults to 1.
        multiprocessing (bool, optional): Flag to enable or disable multiprocessing during cloning. Defaults to False.

    Returns:
        None. The cloned repositories are saved in a predefined directory.
    """

    with progress:

        start_time = time.time()
        if repo_urls is None:
            repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

        if len(repo_urls) == 0:
            logging.error(
                'Repositories list was empty. '
                'Please provide a list of repository URLs or a file that is not empty.')
            return

        logging.info(f'\nCloning {len(repo_urls)} repositories')

        logging.info(f"Cloning will run with the current settings:"
                     f"\n - chunk_size={chunk_size}, multiprocessing={multiprocessing}\n\n"
                     f"\nLog directory\n{config.LOGGING_FOLDER}\n"
                     f"\nRepositories direvtory\n{config.REPOSITORIES_FOLDER}\n\n")

        _process_chunk(repo_urls,
                       pyciras_functions=[_clone_repos],
                       stargazers=False,
                       metadata=False,
                       chunk_size=chunk_size,
                       multiprocessing=multiprocessing,
                       persist_repos=True)

        duration = util.format_duration(time.time() - start_time)

        ntfyer.ntfy(data=f'PyCIRAS cloning completed! Cloned {len(repo_urls)} repos in the duration of: {duration}',
                    title='PyCIRAS cloning Completed')

        logging.info(f"\nPyCIRAS cloning completed - Duration: {duration}.")


def run_mining(repo_urls: list[str] = None,
               chunk_size: int = 1,
               multiprocessing: bool = False,
               persist_repos: bool = True,
               stargazers: bool = True,
               metadata: bool = True,
               lint: bool = True,
               test: bool = True,
               git: bool = True):
    """
    Executes a series of mining operations on a given list of repository URLs to analyze their code quality,
    testing practices, and other characteristics.

    This function can perform several types of analyses, including linting, testing, stargazers, metadata, and Git
    history analysis. The results of these analyses are stored in predefined directories, and the progress is logged
    for monitoring purposes. The mining process can be customized through a set of boolean flags that enable or disable
    specific analyses. Further functionalities can be applied or modified in the config.py file.

    Parameters:
        repo_urls (list[str], optional): A list of repository URLs to be mined. If None, URLs will be loaded from a
            predefined configuration file.
        chunk_size (int, optional): The number of repositories to process in each chunk. Defaults to 1.
        multiprocessing (bool, optional): Enables or disables multiprocessing for the mining operations.
            Defaults to False.
        persist_repos (bool, optional): If True, cloned repositories will be persisted in a local directory.
            Defaults to True.
        stargazers (bool, optional): If True, information about stargazers will be collected for each repository.
            Defaults to True.
        metadata (int, optional): Enable or disable the metadata analysis. Defaults to True.
        lint (bool, optional): Enables or disables linting analysis. Defaults to True.
        test (bool, optional): Enables or disables testing analysis. Defaults to True.
        git (bool, optional): Enables or disables Git history analysis. Defaults to True.

    Returns:
        None. Results of the mining operations are logged and saved in predefined directories.

    Side effects:
        - Clones repositories to the local filesystem, removes them only if persist_repos is False.
        - Logs progress and results to predefined logging and results directories.
        - Notifies the user upon completion of the mining process via a notification system if correctly configured.
    """
    with progress:
        start_time = time.time()
        if repo_urls is None:
            repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

        if len(repo_urls) == 0:
            logging.error(
                'Repositories list was empty. '
                'Please provide a list of repository URLs or a file that is not empty.')
            return

        logging.info(f'\nMining {len(repo_urls)} repositories')

        logging.info(f"The analysis will run with the current settings:"
                     f"\n - chunk_size={chunk_size}, multiprocessing={multiprocessing}"
                     f"\n - persist_repos={persist_repos}"
                     f"\n - stagazers={stargazers}"
                     f"\n - lint={lint}"
                     f"\n - test={test}"
                     f"\n - git={git}\n\n"
                     f"\nData directory\n{data_directory}\n"
                     f"\nLog directory\n{config.LOGGING_FOLDER}\n"
                     f"\nRepositories directory\n{config.REPOSITORIES_FOLDER}\n\n")

        mining_functions = []
        if git:
            mining_functions.append(_mine_git)
        if lint:
            mining_functions.append(_mine_lint)
        if test:
            mining_functions.append(_mine_test)

        _process_chunk(repo_urls,
                       mining_functions,
                       stargazers,
                       metadata,
                       chunk_size,
                       multiprocessing,
                       persist_repos)

        duration = util.format_duration(time.time() - start_time)

        ntfyer.ntfy(data=f'PyCIRAS mining completed! Analyzed {len(repo_urls)} repos in the duration of: {duration}',
                    title='PyCIRAS Mining Completed')
        logging.info(f"\nPyCIRAS Mining completed - Duration: {duration}.")


@timed
def _mine_lint(repo_urls: list[str]):
    """ Mine lint data from a list of repositories. """
    try:
        repo_paths = _clone_repos(repo_urls)

        repos_and_commit_metadata = repo_management.get_repo_paths_and_commit_metadata(config.REPOSITORIES_FOLDER,
                                                                                       repo_paths,
                                                                                       progress)

        logging.info(f'\nMining Lint Data for {repo_urls}')

        lint_data = lint_mining.mine_lint_data(repos_and_commit_metadata, progress)

        if config.WRITE_JSON:
            data_management.write_json(lint_data, data_directory / 'lint-raw.json', progress)

        if config.WRITE_CSV:
            data_management.lint_data_to_csv(lint_data, data_directory / 'lint.csv', progress)

        logging.info(f'\nMINE LINT COMPLETED: {repo_urls}')

    except Exception:
        repos = [util.get_repo_name_from_url_or_path(url) for url in repo_urls]
        logging.error(f'Error while linting repositories {repos}'
                      f'Skipping Mine Lint', exc_info=True)
        return


@timed
def _mine_git(repo_urls: list[str]):
    """ Mine git data from a list of repositories. """
    try:

        logging.info(f'\nMining Git Data for {repo_urls}')

        git_data = git_mining.mine_git_data(config.REPOSITORIES_FOLDER, repo_urls, progress)

        if config.WRITE_JSON:
            data_management.write_json(git_data, data_directory / 'git-raw.json', progress)

        if config.WRITE_CSV:
            data_management.git_data_to_csv(git_data, data_directory / 'git.csv', progress)

        logging.info(f'\nMINE GIT COMPLETED: {repo_urls}')

    except Exception:
        repos = [util.get_repo_name_from_url_or_path(url) for url in repo_urls]
        logging.error(f'Error while mining git repositories {repos}'
                      f'Skipping Mine Git', exc_info=True)
        return


@timed
def _mine_test(repo_urls: list[str]):
    """ Mine test data from a list of repositories. """
    try:
        repo_paths = _clone_repos(repo_urls)

        repos_and_commit_metadata = repo_management.get_repo_paths_and_commit_metadata(config.REPOSITORIES_FOLDER,
                                                                                       repo_paths,
                                                                                       progress)

        logging.info(f'\nMining Test Data for {repo_urls}')

        test_data = test_mining.mine_test_data(repos_and_commit_metadata, progress)

        if config.WRITE_JSON:
            data_management.write_json(test_data, data_directory / 'test-raw.json', progress)

        if config.WRITE_CSV:
            data_management.test_data_to_csv(test_data, data_directory / 'test.csv', progress)

        logging.info(f'\nMINE TEST COMPLETED: {repo_urls}')

    except Exception:
        repos = [util.get_repo_name_from_url_or_path(url) for url in repo_urls]
        logging.error(f'Error while mining test data from repositories {repos}\n'
                      f'Skipping Mine Test', exc_info=True)

        return


@timed
def _mine_stargazers(repo_urls: list[str]):
    """ Mine stargazers data from a list of repositories. """
    try:

        logging.info(f'\nMining Stargazers for {repo_urls}')

        stargazers_data = git_mining.mine_stargazers_data(repo_urls, progress)

        if config.WRITE_JSON:
            data_management.write_json(stargazers_data, data_directory / 'stargazers-raw.json', progress)

        if config.WRITE_CSV:
            data_management.stargazers_data_to_csv(stargazers_data, data_directory / 'stargazers.csv', progress)

        logging.info(f'\nMINE STARGAZERS COMPLETED: {repo_urls}')

    except Exception:
        repos = [util.get_repo_name_from_url_or_path(url) for url in repo_urls]
        logging.error(f'Error while fetching stargazer data for {repos}'
                      f'Skipping Mine Stargazers', exc_info=True)
        return


@timed
def _mine_metadata(repo_urls: list[str]):
    """Mine repo metadata from a list of repositories."""
    try:

        logging.info(f'\nMining Metadata for {repo_urls}')

        metadata = git_mining.mine_repo_metadata(repo_urls, progress)

        if config.WRITE_JSON:
            data_management.write_json(metadata, data_directory / 'metadata-raw.json', progress)

        if config.WRITE_CSV:
            data_management.metadata_to_csv(metadata, data_directory / 'metadata.csv', progress)

            logging.info(f'\nMINE METADATA COMPLETED: {repo_urls}')

    except Exception:
        repos = [util.get_repo_name_from_url_or_path(url) for url in repo_urls]
        logging.error(f'Error while mining metadata data for repositories {repos}'
                      f'Skipping Mine Metadata', exc_info=True)
        return


@timed
def _clone_repos(repo_urls: list[str]) -> list[Path]:
    """Clone a list of repositories."""

    logging.info(f'\nCloning Repos: {repo_urls}')

    return repo_management.clone_repos(config.REPOSITORIES_FOLDER, repo_urls, progress)


def _process_chunk(repo_urls: list[str],
                   pyciras_functions: list[Callable[..., list[Path] | None]],
                   stargazers: bool,
                   metadata: bool,
                   chunk_size: int = 1,
                   multiprocessing: bool = False,
                   persist_repos: bool = True):
    """Processes repos in chunks."""

    if stargazers is False and metadata is False and len(pyciras_functions) == 0:
        logging.error('At least one PyCIRAS function must be selected!')
        return

    if metadata:
        _mine_metadata(repo_urls)

    if stargazers:
        _mine_stargazers(repo_urls)

    if len(pyciras_functions) != 0:
        for i in range(0, len(repo_urls), chunk_size):
            logging.debug(f'Processing repositories {i}-{i + chunk_size}')
            chunk_of_repos = repo_urls[i:i + chunk_size]
            if multiprocessing:
                logging.debug(f'Processing in parallel')
                _execute_in_parallel(args_list=[(pyciras_functions, [repo]) for repo in chunk_of_repos])
            else:
                logging.debug(f'Processing sequentially')
                for function in pyciras_functions:
                    logging.debug(f'Running {str(function.__name__)}')
                    function(chunk_of_repos)
            if not persist_repos:
                logging.debug(f'Deleting Repos')
                repo_management.remove_repos(chunk_of_repos)


def _execute_in_parallel(args_list: list):
    """ Executes a function in parallel with arguments. """

    def run_all(pyricas_functions, urls):
        result = {}
        for function in pyricas_functions:
            result[str(function.__name__)] = function(urls)
        return result

    with ThreadPoolExecutor() as pool:
        for args in args_list:
            pool.submit(run_all, *args)


if __name__ == '__main__':
    run_repo_cloner(repo_urls=None,
                    chunk_size=100,
                    multiprocessing=True)

    run_mining(repo_urls=None,
               chunk_size=1,
               multiprocessing=False,
               persist_repos=True,  # Testa false, tar den bort nedladdade?
               stargazers=True,
               metadata=True,
               test=True,
               git=True,
               lint=True)
