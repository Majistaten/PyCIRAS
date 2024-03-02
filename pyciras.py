from analysis import code_quality, git_miner, repo_cloner
from datahandling import data_writer, data_converter
from utility import util, config


# TODO skapa möjligheten att dra gång flera processer som analyserar samtidigt och skriver resultat efter varje analys

# TODO skapa massa run metoder för användning från notebooks

# TODO allow passing the file with repository URLs to the method

def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    # Download repositories
    repo_paths = repo_cloner.download_repositories(repo_urls_path=config.REPOSITORY_URLS,
                                                   destination_folder=config.REPOSITORIES_FOLDER)
    repo_urls = util.get_repository_urls_from_file(config.REPOSITORY_URLS)

    # Mine data
    pydriller_data = git_miner.mine_pydriller_metrics(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)
    repositories_with_commits = git_miner.get_commit_dates(repo_paths, repository_directory=config.REPOSITORIES_FOLDER)
    pylint_data = code_quality.mine_pylint_metrics(repositories_with_commits)

    # Create data directory for the analysis
    data_directory = data_writer.create_timestamped_data_directory()

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


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
