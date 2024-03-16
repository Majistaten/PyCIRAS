"""This module provides the main entry point for the PyCIRAS application and the main mining functionality."""

import concurrent.futures
import logging
import rich.traceback
from typing import Callable
from mining import lint_mining, git_mining, test_mining
from data_io import data_file_management, data_manipulation, repo_management
from utility import util, config, logger_setup, ntfyer

rich.traceback.install()
data_directory = data_file_management.create_timestamped_data_directory()  # TODO ska denna flyttas in i run_mining istället?
logger = logger_setup.get_logger('pyciras_logger')


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
                title='PyCIRAS Completed')


def _mine_lint(repo_urls: list[str]) -> dict[str, any]:
    repo_paths = repo_management.download_repositories(repo_urls=repo_urls,
                                                       destination_folder=config.REPOSITORIES_FOLDER)

    repos_hashes = git_mining.get_repos_commit_metadata(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)

    pylint_data = lint_mining.mine_lint_metrics(repos_hashes)

    pylint_data_filtered = data_manipulation.remove_pylint_messages(pylint_data)
    pylint_data_filtered_flat = data_manipulation.flatten_pylint_data(pylint_data_filtered)
    pylint_data_cleaned = data_manipulation.clean_pylint_data(pylint_data_filtered_flat)

    data_file_management.write_json_data(pylint_data, data_directory / 'pylint-raw.json')
    data_file_management.write_json_data(pylint_data_filtered_flat, data_directory / 'pylint-raw-flat.json')
    data_file_management.pylint_data_csv(pylint_data_cleaned, data_directory)

    return pylint_data


def _mine_git(repo_urls: list[str]) -> dict[str, any]:

    #TODO varför används ej?
    repo_paths = repo_management.download_repositories(repo_urls=repo_urls,
                                                       destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    pydriller_data = git_mining.mine_pydriller_metrics(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)
    # pydriller_data = git_mining.mine_pydriller_metrics(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)

    # write json to file
    data_file_management.write_json_data(pydriller_data, data_directory / 'pydriller-raw.json')

    # Flatten the data
    pydriller_data_flat = data_manipulation.flatten_pydriller_data(pydriller_data)

    # write json to file
    data_file_management.write_json_data(pydriller_data_flat, data_directory / 'pydriller-flat.json')

    # write csv to file
    data_file_management.pydriller_data_csv(pydriller_data_flat, data_directory)

    return pydriller_data

# TODO progressbar stannar om det kastas error för ett syntax error i en fil
def _mine_test(repo_urls: list[str]) -> dict[str, any]:
    repo_paths = repo_management.download_repositories(repo_urls=repo_urls,
                                                       destination_folder=config.REPOSITORIES_FOLDER)

    repositories_with_commits = git_mining.get_repos_commit_metadata(repo_paths,
                                                                     repository_directory=
                                                                     config.REPOSITORIES_FOLDER)

    # gather metric data
    unit_testing_metrics = test_mining.mine_unit_testing_metrics(repositories_with_commits)

    # write json to file
    data_file_management.write_json_data(unit_testing_metrics, data_directory / 'unit-testing-raw.json')

    # Extract test to code ratio over time
    # TODO Rename
    test_to_code_ratio_over_time = data_manipulation.get_test_to_code_ratio_over_time(unit_testing_metrics)

    # write json to file
    data_file_management.write_json_data(test_to_code_ratio_over_time,
                                         data_directory / 'test-to-code-ratio-over-time.json')

    # write csv to file
    data_file_management.unit_testing_data_csv(test_to_code_ratio_over_time, data_directory)

    return unit_testing_metrics


def _mine_stargazers(repo_urls: list[str]) -> dict[str, any]:
    try:
        stargazers_metrics = git_mining.mine_stargazers_metrics(repo_urls)
    except ValueError as e:
        logging.error(e)
        return
    except Exception as e:
        logging.error(f'Something unexpected happened: {e}')
        return

    data_file_management.write_json_data(stargazers_metrics, data_directory / 'stargazers-raw.json')

    # Clean the data
    stargazers_metrics = data_manipulation.clean_stargazers_data(stargazers_metrics)

    data_file_management.write_json_data(stargazers_metrics, data_directory / 'stargazers-cleaned.json')

    # Extract stargazers over time
    stargazers_over_time = data_manipulation.get_stargazers_over_time(stargazers_metrics)

    data_file_management.write_json_data(stargazers_over_time, data_directory / 'stargazers-over-time.json')
    data_file_management.stargazers_data_csv(stargazers_over_time, data_directory)

    return stargazers_metrics




# TODO implement
def run_repo_cloner():
    pass


# TODO döp om
# TODO refaktorera
def _process_chunk(repo_urls: list[str],
                   mining_functions: list[Callable[..., dict[str, any]]],
                   stargazers: bool,
                   chunk_size: int = 1,
                   multiprocessing: bool = False,
                   persist_repos: bool = True):
    """Processes repos in chunks."""

    if stargazers is False and len(mining_functions) == 0:
        raise ValueError('At least one mining function must be selected!')

    for i in range(0, len(repo_urls), chunk_size):
        logging.info(f'Mining repositories {i}-{i + chunk_size}')
        chunk_of_repos = repo_urls[i:i + chunk_size]
        if multiprocessing:
            logging.info(f'Mining in parallel')
            _execute_in_parallel(args_list=[(mining_functions, [repo]) for repo in chunk_of_repos],
                                 workers=chunk_size)
        else:
            logging.info(f'Mining sequentially')
            for function in mining_functions:
                logging.info(f'Running {str(function.__name__)}')
                function(chunk_of_repos)
        if not persist_repos:
            repo_management.remove_repos(chunk_of_repos)
    if stargazers:
        _mine_stargazers(repo_urls)


def _execute_in_parallel(args_list: list, workers: int = 4):
    """Executes a function in parallel with arguments."""

    def run_all(mining_functions, urls):
        result = {}
        for function in mining_functions:
            logging.info(f'Running {str(function.__name__)} on {urls}')
            result[str(function.__name__)] = function(urls)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(run_all, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == '__main__':
    run_mining(repo_urls=None,
               chunk_size=1,
               multiprocessing=False,
               persist_repos=True,
               stargazers=True,
               test=True,
               git=True,
               lint=True)
