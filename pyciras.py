import concurrent.futures
import time
from typing import Callable
from git import rmtree

from analysis import code_quality, git_miner, repo_cloner
from datahandling import data_writer, data_converter
from utility import util, config


# TODO skapa möjligheten att dra gång flera processer som analyserar samtidigt och skriver resultat efter varje analys

# TODO skapa massa run metoder för användning från notebooks

# TODO allow passing the file with repository URLs to the method

# Create data directory for the analysis
data_directory = data_writer.create_timestamped_data_directory()


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
            process_group(current_group, use_subprocesses)
    return None


def execute_in_parallel(func: Callable[..., str], args_list: list, max_workers: int = 4):
    """Executes a function in parallel given a list of arguments."""
    print(f"Executing {len(args_list)} blabla of {args_list}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(func, *args) for args in args_list]
        for future in concurrent.futures.as_completed(futures):
            try:
                print(future.result())
            except Exception as e:
                print(f'Exception caught here: {e}')


def process_group(current_group: list[str], remove_repo_on_complete: bool = True):
    print(current_group)
    repo_paths = repo_cloner.download_repositories(repo_url_list=current_group,
                                                   destination_folder=config.REPOSITORIES_FOLDER)

    # gather metric data
    pydriller_data = git_miner.mine_pydriller_metrics(current_group, repository_directory=config.REPOSITORIES_FOLDER)
    repositories_with_commits = git_miner.get_commit_dates(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)
    pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)

    # write json to file
    data_writer.pydriller_data_json(pydriller_data, data_directory)
    data_writer.pylint_data_json(pylint_data, data_directory)

    # Remove unwanted data for csv
    pylint_data = data_converter.remove_pylint_messages(pylint_data)

    # Flatten the data
    pydriller_data = data_converter.flatten_pydriller_data(pydriller_data)
    pylint_data = data_converter.flatten_pylint_data(pylint_data)

    # write csv to file
    data_writer.pydriller_data_csv(pydriller_data, data_directory)
    data_writer.pylint_data_csv(pylint_data, data_directory)

    if remove_repo_on_complete:
        remove_repositories(current_group)
    return "Finished"


def remove_repositories(content: list[str]):
    print(f'Removing {len(content)} repositories {content}')
    for url in content:
        path = util.get_path_to_repo(url)
        if path.index(config.REPOSITORIES_FOLDER) > -1:
            print(f'Removing: {path}\n')
            rmtree(path)
        else:
            print(f'Something went wrong with the path extraction for {url}, got path {path}')
    pass


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    load_balancing(repo_urls=util.get_repository_urls_from_file(config.REPOSITORY_URLS), group_size=5,
                   use_subprocesses=True, remove_repos_after_completion=True)
    # repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)
    # # Download repositories
    # repo_paths = repo_cloner.download_repositories(repo_url_list=repo_urls,
    #                                                destination_folder=config.REPOSITORIES_FOLDER)
    #
    # # Mine data
    # pydriller_data = git_miner.mine_pydriller_metrics(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)
    # repositories_with_commits = git_miner.get_commit_dates(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)
    # pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)
    #
    # # Create data directory for the analysis
    # data_directory = data_writer.create_timestamped_data_directory()
    #
    # # write json to file
    # data_writer.pydriller_data_json(pydriller_data, data_directory)
    # data_writer.pylint_data_json(pylint_data, data_directory)
    #
    # # Remove unwanted data for csv
    # pylint_data = data_converter.remove_pylint_messages(pylint_data)
    #
    # # Flatten the data
    # pydriller_data = data_converter.flatten_pydriller_data(pydriller_data)
    # pylint_data = data_converter.flatten_pylint_data(pylint_data)
    #
    # # write csv to file
    # data_writer.pydriller_data_csv(pydriller_data, data_directory)
    # data_writer.pylint_data_csv(pylint_data, data_directory)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
