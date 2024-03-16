import concurrent.futures
import logging
import rich.traceback
from typing import Callable
from mining import code_quality, git_miner, repo_cloner, unit_testing
from data_io import data_file_management, data_manipulation
from utility import util, config, logger_setup, ntfyer

rich.traceback.install()
data_directory = data_file_management.create_timestamped_data_directory()
logger = logger_setup.get_logger("pyciras_logger")

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

def run_mining(repo_urls: list[str] = None,
               chunk_size: int = 3,
               multiprocessing: bool = False,
               persist_repos: bool = True,
               stargazers: bool = True,
               code_quality: bool = True,
               unit_testing: bool = True,
               git_mining: bool = True, ):
    """"Execute the specified mining on a list of repositories."""

    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    logging.info(f"Running mining on {len(repo_urls)} repositories.")
    analysis_methods = []
    if code_quality:
        analysis_methods.append(_code_quality)
    if git_mining:
        analysis_methods.append(run_pydriller_analysis)
    if unit_testing:
        analysis_methods.append(run_unit_testing_analysis)

    _load_balancing(repo_urls,
                    chunk_size,
                    multiprocessing,
                    persist_repos,
                    analysis_methods,
                    stargazers)

    ntfyer.ntfy(data=f"The execution has completed, {len(repo_urls)} repositories were analyzed.",
                title="Pyciras complete")


# TODO döp om metoder så de heter något mer beskrivande, t.ex code quality, git metrics, inte pydriller
def _code_quality(repo_urls: list[str]) -> dict[str, any]:

    repo_paths = repo_cloner.download_repositories(repo_urls_list=repo_urls,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    repositories_with_commits = git_miner.get_repo_paths_with_commit_hashes_and_dates(repo_paths,
                                                                                      repository_directory=config.REPOSITORIES_FOLDER)
    pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)

    # write json to file
    data_file_management.write_json_data(pylint_data, data_directory / 'pylint-raw.json')

    # Remove unwanted pylint messages
    pylint_data_filtered = data_manipulation.remove_pylint_messages(pylint_data)

    # Flatten the data
    pylint_data_filtered_flat = data_manipulation.flatten_pylint_data(pylint_data_filtered)

    # write json to file
    data_file_management.write_json_data(pylint_data_filtered_flat, data_directory / 'pylint-raw-flat.json')

    # Remove unwanted data points and prepare for csv
    pylint_data_cleaned = data_manipulation.clean_pylint_data(pylint_data_filtered_flat)

    # write csv to file
    data_file_management.pylint_data_csv(pylint_data_cleaned, data_directory)

    return pylint_data


def run_pydriller_analysis(repo_urls: list[str]) -> dict[str, any]:

    repo_paths = repo_cloner.download_repositories(repo_urls_list=repo_urls,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    pydriller_data = git_miner.mine_pydriller_metrics(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)

    # write json to file
    data_file_management.write_json_data(pydriller_data, data_directory / 'pydriller-raw.json')

    # Flatten the data
    pydriller_data_flat = data_manipulation.flatten_pydriller_data(pydriller_data)

    # write json to file
    data_file_management.write_json_data(pydriller_data_flat, data_directory / 'pydriller-flat.json')

    # write csv to file
    data_file_management.pydriller_data_csv(pydriller_data_flat, data_directory)

    return pydriller_data

# TODO name mangla alla metoder och ta bort run_ prefixet
# Refaktorera ut all dataskrivning till runmetoden, returnera bara metrics istället - få bort massa side effects of duplicerad kod
def run_stargazers_analysis(repo_urls: list[str]) -> dict[str, any]:

    try:
        stargazers_metrics = git_miner.mine_stargazers_metrics(repo_urls)
    except ValueError as e:
        logging.error(e)
        return
    except Exception as e:
        logging.error(f"Something unexpected happened: {e}")
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


def run_unit_testing_analysis(repo_urls: list[str]) -> dict[str, any]:

    repo_paths = repo_cloner.download_repositories(repo_urls_list=repo_urls,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    repositories_with_commits = git_miner.get_repo_paths_with_commit_hashes_and_dates(repo_paths,
                                                                                      repository_directory=
                                                                                      config.REPOSITORIES_FOLDER)

    # gather metric data
    unit_testing_metrics = unit_testing.mine_unit_testing_metrics(repositories_with_commits)

    # write json to file
    data_file_management.write_json_data(unit_testing_metrics, data_directory / 'unit-testing-raw.json')

    # Extract test to code ratio over time
    # TODO Rename
    test_to_code_ratio_over_time = data_manipulation.get_test_to_code_ratio_over_time(unit_testing_metrics)

    # write json to file
    data_file_management.write_json_data(test_to_code_ratio_over_time, data_directory / 'test-to-code-ratio-over-time.json')

    # write csv to file
    data_file_management.unit_testing_data_csv(test_to_code_ratio_over_time, data_directory)

    return unit_testing_metrics


# TODO implement
def run_repo_cloner():
    pass

# TODO döp om
# TODO refaktorera
def _load_balancing(repo_urls: list[str],
                    chunk_size: int = 1,
                    parallelism: bool = False,
                    remove_repos_after_completion: bool = True,
                    analysis_methods: list[Callable[..., dict[str, any]]] | None = None,
                    analyze_stargazers: bool = True):
    """Handles repositories in groups. Downloads and analyzes the repositories one group at a time,
     stores the result and removes the repository when done."""
    if analyze_stargazers is False and (analysis_methods is None or len(analysis_methods) == 0):
        raise ValueError('At least one mining method must be selected!')
    for i in range(0, len(repo_urls), chunk_size):
        logging.info(f"Analyzing repositories {i}-{i + chunk_size}")
        current_group = repo_urls[i:i + chunk_size]
        if parallelism:
            _execute_in_parallel(args_list=[(analysis_methods, [repo]) for repo in current_group],
                                 max_workers=chunk_size)
        else:
            for method in analysis_methods:
                logging.info(f"Running {str(method.__name__)}")
                method(current_group)
        if not remove_repos_after_completion:
            repo_cloner.remove_repositories(current_group)
    if analyze_stargazers:
        run_stargazers_analysis(repo_urls)


def _execute_in_parallel(args_list: list, max_workers: int = 4):
    """Executes a function in parallel given a list of arguments."""

    def run_all(methods, urls):
        result = {}
        for method in methods:
            logging.info(f"Running {str(method.__name__)} on {urls}")
            result[str(method.__name__)] = method(urls)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run_all, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == '__main__':
    run_mining(repo_urls=None,
               chunk_size=1,
               multiprocessing=False,
               persist_repos=True,
               stargazers=True,
               unit_testing=True,
               git_mining=True,
               code_quality=True)
