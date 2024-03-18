"""This module provides the main entry point for the PyCIRAS application and the main mining functionality."""

# TODO BASIC Unit testing för projektkraven, coveragePy coverage checking
# TODO Skriv docs på allt, inklusive moduler, parametrar, typer, och README
# TODO linta, döp om saker, refaktorera allmänt
# TODO gör så att raw data skrivs till /out/data/repo/raw och processad data till /out/data/repo/processed
# TODO dumpa settings och inställningar i logger för varje körning om vilken config som användes när den kördes
# TODO name mangla individuella runmetoder
# TODO verifiera all CSV mot raw-data
# TODO gå igenom linter issues och fixa allt
# TODO insertera log statements på alla olika execution branches på info-nivå
# TODO kolla .pylintrc settings så man får ut cyclomatic complexity och alla andra intressanta metrics - inte säkert att man får det nu
# TODO få ut complexity metrics från pydriller också?
# TODO progressbar stannar om det kastas error för ett syntax error i en fil under unit testing analysis
# TODO error handling här i denna filen?
# TODO byt alla NaN till nan

import concurrent.futures
import logging
from pathlib import Path

import rich.traceback
from typing import Callable
from mining import lint_mining, git_mining, test_mining
from data_io import data_file_management, data_manipulation, repo_management
from utility import util, config, logger_setup, ntfyer

rich.traceback.install()
data_directory = data_file_management.make_data_directory()  # TODO ska denna flyttas in i run_mining istället?
logger = logger_setup.get_logger('pyciras_logger')


# TODO fixa bättre docstrings som förklarar parametrar
def run_repo_cloner(repo_urls: list[str] = None,
                    chunk_size: int = 1,
                    multiprocessing: bool = False):
    """Clone repos from a list of URLs or a file containing a list of URLs."""
    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    if len(repo_urls) == 0:
        logging.error(
            'Repositories list was empty. '
            'Please provide a list of repository URLs or a file that is not empty.')
        return

    logging.info(f'Cloning {len(repo_urls)} repositories')

    _process_chunk(repo_urls,
                   pyciras_functions=[_clone_repos],
                   stargazers=False,
                   chunk_size=chunk_size,
                   multiprocessing=multiprocessing,
                   persist_repos=True)

    ntfyer.ntfy(data=f'PyCIRAS cloning completed, {len(repo_urls)} repos',
                title='PyCIRAS Cloning Completed')


# TODO fixa bättre docstrings som förklarar parametrar
# TODO Bool för att få ut JSON/CSV/inte
def run_mining(repo_urls: list[str] = None,
               chunk_size: int = 1,
               multiprocessing: bool = False,
               persist_repos: bool = True,
               stargazers: bool = True,
               lint: bool = True,
               test: bool = True,
               git: bool = True):
    """"Execute the specified mining on a list of repositories."""

    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    if len(repo_urls) == 0:
        logging.error(
            'Repositories list was empty. '
            'Please provide a list of repository URLs or a file that is not empty.')
        return

    logging.info(f'Mining {len(repo_urls)} repositories')
    logging.info(f"The analysis will run with the current settings: "
                 f"\n - chunk_size={chunk_size}, multiprocessing={multiprocessing}, "
                 f"\n - persist_repos={persist_repos}, "
                 f"\n - stagazers={stargazers}, "
                 f"\n - lint={lint}, "
                 f"\n - test={test}, "
                 f"\n - git={git}."
                 f"\n   Results will be stored in {data_directory}."
                 f"\n   Logging will be stored in {config.LOGGING_FOLDER}."
                 f"\n   Repositories will be stored in {config.REPOSITORIES_FOLDER}.")

    mining_functions = []
    if lint:
        mining_functions.append(_mine_lint)
    if git:
        mining_functions.append(_mine_git)
    if test:
        mining_functions.append(_mine_test)

    _process_chunk(repo_urls,
                   mining_functions,
                   stargazers,
                   chunk_size,
                   multiprocessing,
                   persist_repos)

    ntfyer.ntfy(data=f'PyCIRAS mining completed, {len(repo_urls)} repos',
                title='PyCIRAS Mining Completed')


# TODO kalla data_management för att mangla med pandas, sen en skrivmetod i samma fil för att skriva
def _mine_lint(repo_urls: list[str]):
    """"Mine lint data from a list of repositories."""

    repo_paths = _clone_repos(repo_urls)

    repos_and_commit_metadata = git_mining.get_repos_commit_metadata(config.REPOSITORIES_FOLDER, repo_paths)
    lint_data = lint_mining.mine_lint_data(repos_and_commit_metadata)

    lint_data_no_msg = data_manipulation.remove_lint_messages(lint_data)
    lint_data_no_msg_flat = data_manipulation.flatten_lint_data(lint_data_no_msg)
    lint_data_clean = data_manipulation.clean_lint_data(lint_data_no_msg_flat)

    data_file_management.write_json(lint_data, data_directory / 'lint-raw.json')
    data_file_management.write_json(lint_data_no_msg, data_directory / 'lint-no-msg.json')
    data_file_management.write_json(lint_data_no_msg_flat, data_directory / 'lint-no-msg-flat.json')
    # TODO fixa i clean funktionen så det inte är datettime objekt i, annars funkar inte denna skrivning
    # data_file_management.write_json(lint_data_clean, data_directory / 'lint-clean.json')
    data_file_management.write_lint_csv(lint_data_clean, data_directory)


def _mine_git(repo_urls: list[str]):
    """Mine git data from a list of repositories."""

    git_data = git_mining.mine_git_data(config.REPOSITORIES_FOLDER, repo_urls)
    git_data_flat = data_manipulation.flatten_git_data(git_data)

    data_file_management.write_json(git_data, data_directory / 'git-raw.json')
    data_file_management.write_json(git_data_flat, data_directory / 'git-flat.json')
    data_file_management.write_git_csv(git_data_flat, data_directory / 'git-flat.csv')


def _mine_test(repo_urls: list[str]):
    """"Mine test data from a list of repositories."""

    repo_paths = _clone_repos(repo_urls)

    repos_and_commit_metadata = git_mining.get_repos_commit_metadata(config.REPOSITORIES_FOLDER, repo_paths)
    test_data = test_mining.mine_test_data(repos_and_commit_metadata)

    test_data_over_time = data_manipulation.get_test_data_over_time(test_data)

    data_file_management.write_json(test_data, data_directory / 'test-raw.json')
    data_file_management.write_json(test_data_over_time, data_directory / 'test-over-time.json')
    data_file_management.write_test_csv(test_data_over_time, data_directory / 'test-over-time.csv')


def _mine_stargazers(repo_urls: list[str]):
    """Mine stargazers data from a list of repositories."""

    stargazers_data = git_mining.mine_stargazers_data(repo_urls)
    # repo_lifespans = git_mining.get_repo_lifespans(stargazers_data)

    stargazers_data_clean = data_manipulation.clean_stargazers_data(stargazers_data)
    stargazers_over_time = data_manipulation.stargazers_over_time(stargazers_data_clean)

    data_file_management.write_json(stargazers_data, data_directory / 'stargazers-raw.json')
    data_file_management.write_json(stargazers_data_clean, data_directory / 'stargazers-clean.json')
    data_file_management.write_json(stargazers_over_time, data_directory / 'stargazers-over-time.json')
    data_file_management.write_stargazers_csv(stargazers_over_time, data_directory / 'stargazers-over-time.csv')


def _mine_lifespan(repo_urls: list[str]):
    """ Mine dates from the project lifespan from a list of repositories. """
    # TODO: Print to json/csv etc..
    lifespan_data = git_mining.get_repositories_lifespan(repo_urls)


# TODO lägg in så man kan skippa repos av viss size?
def _clone_repos(repo_urls: list[str]) -> list[Path]:
    """Clone a list of repositories."""
    return repo_management.prepare_repositories(config.REPOSITORIES_FOLDER, repo_urls)


# TODO heltäckande error handling i denna?
def _process_chunk(repo_urls: list[str],
                   pyciras_functions: list[Callable[..., list[Path] | None]],
                   stargazers: bool,
                   chunk_size: int = 1,
                   multiprocessing: bool = False,
                   persist_repos: bool = True):
    """Processes repos in chunks."""

    if stargazers is False and len(pyciras_functions) == 0:
        logging.error('At least one pyciras function must be selected!')
        return

    for i in range(0, len(repo_urls), chunk_size):
        logging.info(f'Processing repositories {i}-{i + chunk_size}')
        chunk_of_repos = repo_urls[i:i + chunk_size]
        if multiprocessing:
            logging.info(f'Processing in parallel')
            _execute_in_parallel(args_list=[(pyciras_functions, [repo]) for repo in chunk_of_repos],
                                 workers=chunk_size)
        else:
            logging.info(f'Processing sequentially')
            for function in pyciras_functions:
                logging.info(f'Running {str(function.__name__)}')
                function(chunk_of_repos)
        if not persist_repos:
            repo_management.remove_repos(chunk_of_repos)
    if stargazers:
        _mine_stargazers(repo_urls)


def _execute_in_parallel(args_list: list, workers: int = 4):
    """Executes a function in parallel with arguments."""

    def run_all(pyricas_functions, urls):
        result = {}
        for function in pyricas_functions:
            logging.info(f'Running {str(function.__name__)} on {urls}')
            result[str(function.__name__)] = function(urls)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_all, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == '__main__':
    # run_repo_cloner(repo_urls=None,
    #                 chunk_size=3,
    #                 multiprocessing=True)
    run_mining(repo_urls=None,
               chunk_size=1,
               multiprocessing=False,
               persist_repos=True,
               stargazers=True,
               test=True,
               git=True,
               lint=True)
