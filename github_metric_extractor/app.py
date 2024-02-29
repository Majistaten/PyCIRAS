from datetime import datetime
import csv
import itertools
import repository_downloader
import git_extraction
import logging
import json
import code_aspect_analyzer


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    repository_paths = repository_downloader.download_repositories(repo_url_file='../repos.txt',
                                                                   destination_folder='../repositories')
    metrics = git_extraction.process_repositories(repository_paths, clone_repo_to="../repositories")
    repo_commits = {v["repository_address"]: v["commits"] for (_, v) in metrics.items()}
    code_aspects = code_aspect_analyzer.analyze_repositories_commits(repo_commits)

    with open('./test_out.json', 'w') as file:
        json.dump(metrics, file, indent=4)

    # TODO chrashar pga att sets inte är serializable i JSON
    with open('./code_aspects.json', 'w') as file:
        json.dump(code_aspects, file, indent=4, cls=CustomEncoder)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
