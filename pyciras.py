import concurrent.futures
import json
from pathlib import Path
from typing import Callable
from analysis import code_quality, git_miner, repo_cloner
from datahandling import data_writer, data_converter
from utility import util, config, ntfyer

data_directory = data_writer.create_timestamped_data_directory()

# TODO
# 1. Bygg modulär logger som loggar med rätt färger beroende på nivå
# 2. Bygg modulär progressbar med rich som körs som decorator på grejer om den är enabled
# 3. Error handling i alla metoder med bra meddelanden
# 4. Fixa modulär ntfyer
# 5. Unit testing för projektkraven
# 6. Skriv docs på allt, inklusive moduler, parametrar, typer, och README samt exempelnotebooks
# 7. Fixa runmetoder som tar emot options för alla tänkta användningsområden
# Användningsområden:
# * Köra varje analystyp enskilt
# * Köra hela analysen
# * Köra analysen utan att spara repos
# * Dela upp analysen och skrivningar i chunks
#     * Köra analysen parallellt
# * Optional logging (Flytta logging till config)/ progress bar


def run_full_analysis(repo_urls: list[str] | None = None):
    pass


def run_code_quality_analysis(repo_urls: list[str] | None = None):
    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    repo_paths = repo_cloner.download_repositories(repo_urls_list=repo_urls,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    repositories_with_commits = git_miner.get_commit_dates(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)
    pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)

    # write json to file
    data_writer.write_json_data(pylint_data, data_directory / 'pylint_metrics.json')

    # Remove unwanted data for csv
    pylint_data = data_converter.remove_pylint_messages(pylint_data)

    # Flatten the data
    pylint_data = data_converter.flatten_pylint_data(pylint_data)

    # write csv to file
    data_writer.pylint_data_csv(pylint_data, data_directory)


def run_pydriller_analysis(repo_urls: list[str] | None = None):
    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    repo_paths = repo_cloner.download_repositories(repo_urls_list=repo_urls,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    pydriller_data = git_miner.mine_pydriller_metrics(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)

    # write json to file
    data_writer.write_json_data(pydriller_data, data_directory / 'pydriller_metrics.json')

    # Flatten the data
    pydriller_data = data_converter.flatten_pydriller_data(pydriller_data)

    # write csv to file
    data_writer.pydriller_data_csv(pydriller_data, data_directory)


def run_stargazers_analysis(repo_urls: list[str] | None = None):
    if repo_urls is None:
        repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    stargazers_metrics = git_miner.mine_stargazers_metrics(repo_urls)
    data_writer.write_json_data(stargazers_metrics, data_directory / 'stargazers.json')

    # Clean the data
    stargazers_metrics = data_converter.clean_stargazers_data(stargazers_metrics)

    data_writer.write_json_data(stargazers_metrics, data_directory / 'cleaned-stargazers.json')

    # Extract stargazers over time
    stargazers_over_time = data_converter.get_stargazers_over_time(stargazers_metrics)

    data_writer.write_json_data(stargazers_over_time, data_directory / 'stargazers-over-time.json')
    data_writer.stargazers_data_csv(stargazers_over_time, data_directory)


def run_unit_testing_analysis():
    pass


def run_repo_cloner():
    pass


def _load_balancing(repo_urls: list[str],
                    group_size: int = 4,
                    use_subprocesses: bool = False,
                    remove_repos_after_completion: bool = True):
    """Handles repositories in groups. Downloads and analyzes the repositories one group at a time,
     stores the result and removes the repository when done."""
    for i in range(0, len(repo_urls), group_size):
        current_group = repo_urls[i:i + group_size]
        if use_subprocesses:
            _execute_in_parallel(func=_process_group,
                                 args_list=[([repo], remove_repos_after_completion) for repo in current_group],
                                 max_workers=group_size)
        else:
            _process_group(current_group, remove_repos_after_completion)


def _execute_in_parallel(func: Callable[..., str], args_list: list, max_workers: int = 4):
    """Executes a function in parallel given a list of arguments."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())


def _process_group(current_group: list[str], remove_repo_on_complete: bool = True):
    run_code_quality_analysis(current_group)
    run_pydriller_analysis(current_group)
    run_stargazers_analysis(current_group)
    if remove_repo_on_complete:
        repo_cloner.remove_repositories(current_group)
    return "Finished"


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    _load_balancing(repo_urls=util.get_repository_urls_from_file(config.REPOSITORY_URLS), group_size=3,
                    use_subprocesses=False, remove_repos_after_completion=False)

    # ntfyer.ntfy(data="Execution is complete.", title="Pyciras")


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
