import concurrent.futures
import json
from typing import Callable
from analysis import code_quality, git_miner, repo_cloner
from datahandling import data_writer, data_converter
from utility import util, config, ntfyer

# TODO
# 1. Fixa stargazers och unit_testing analysis
# 2. Fixa massa runmetoder som motsvarar kraven vi satt i rapporten, att users ska kunna göra
# 3. Snygga till output med färger och format, bygg in massa error handling
# 4. Unit testing

# TODO skapa möjligheten att dra gång flera processer som analyserar samtidigt och skriver resultat efter varje analys

# TODO skapa massa run metoder för användning från notebooks

# TODO allow passing the file with repository URLs to the method

# TODO: Vid para körningar, ta bort onödiga headers från CSV och laga JSON

# TODO: Do not remove list, eller möjlighet att tagga repos som inte ska tas bort

# Create data directory for the analysis
# TODO problem med notebooks med detta - blir att denna körs en gång per notebook? eller är det bra?
data_directory = data_writer.create_timestamped_data_directory()


def run_stargazers_analysis():
    # TODO skriver bara JSON än så länge
    # TODO behöver repo namn i datan
    stargazers_metrics = git_miner.mine_stargazers_metrics(util.get_repository_urls_from_file(config.REPOSITORY_URLS))
    data_writer.write_json_data(stargazers_metrics, data_directory / 'stargazers.json')

    # Clean the data
    stargazers_metrics = data_converter.clean_stargazers_data(stargazers_metrics)

    # TODO remove
    # output_path = 'cleaned_stargazers.json'
    # with open(str(output_path), 'w') as file:
    #     json.dump(stargazers_metrics, file, indent=4)

    # TODO implement formatting and CSV writing


def load_balancing(repo_urls: list[str], group_size: int = 4, use_subprocesses: bool = False,
                   remove_repos_after_completion: bool = True):
    """Handles repositories in groups.
    Downloads and analyzes the repositories one group at a time, stores the result and removes the repository when done.
    """
    for i in range(0, len(repo_urls), group_size):
        current_group = repo_urls[i:i + group_size]
        if use_subprocesses:
            execute_in_parallel(func=process_group, args_list=[([repo], remove_repos_after_completion) for repo in current_group], max_workers=group_size)
        else:
            process_group(current_group, remove_repos_after_completion)
    # TODO: clean up the mess you have made in out!


def execute_in_parallel(func: Callable[..., str], args_list: list, max_workers: int = 4):
    """Executes a function in parallel given a list of arguments."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())


def process_group(current_group: list[str], remove_repo_on_complete: bool = True):
    print(current_group)
    repo_paths = repo_cloner.download_repositories(repo_urls_list=current_group,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    pydriller_data = git_miner.mine_pydriller_metrics(current_group, repository_directory=config.REPOSITORIES_FOLDER)
    repositories_with_commits = git_miner.get_commit_dates(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)
    pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)

    # write json to file
    data_writer.write_json_data(pydriller_data, data_directory / 'pydriller_metrics.json')
    data_writer.write_json_data(pylint_data, data_directory / 'pylint_metrics.json')

    # Remove unwanted data for csv
    pylint_data = data_converter.remove_pylint_messages(pylint_data)

    # Flatten the data
    pydriller_data = data_converter.flatten_pydriller_data(pydriller_data)
    pylint_data = data_converter.flatten_pylint_data(pylint_data)

    # write csv to file
    data_writer.pydriller_data_csv(pydriller_data, data_directory)
    data_writer.pylint_data_csv(pylint_data, data_directory)

    # run_stargazers_analysis()
    if remove_repo_on_complete:
        repo_cloner.remove_repositories(current_group)
    return "Finished"


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    load_balancing(repo_urls=util.get_repository_urls_from_file(config.REPOSITORY_URLS), group_size=3,
                   use_subprocesses=False, remove_repos_after_completion=True)

    ntfyer.ntfy(data="Execution is complete.", title="Pyciras")


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
