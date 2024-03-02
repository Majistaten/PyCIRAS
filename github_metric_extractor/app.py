from datetime import datetime
import repo_cloner
import git_miner
import json
import code_quality
import csv_builder

repositories_path = '../repositories/'


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


# TODO skapa möjligheten att dra gång flera processer som analyserar samtidigt och skriver resultat efter varje analys

def main():
    """Test script for downloading repos, extracting metrics and printing to file"""

    repository_paths = repo_cloner.download_repositories(repo_url_file='../repos.txt',
                                                         destination_folder=repositories_path)
    addr = []
    with open("../repos.txt", 'r') as file:
        for line in file:
            addr.append(line)

    metrics = git_miner.mine_pydriller_metrics(addr, repository_directory=repositories_path)
    repo_commits = git_miner.get_commit_dates(repository_paths, repository_directory=repositories_path)
    code_aspects = code_quality.mine_pylint_metrics(repo_commits)

    # TODO: removes messages - find a better solution
    for repo, value in code_aspects.items():
        if value is None:
            continue
        for commit, v in value.items():
            if v is None:
                continue
            v.pop("messages")

    flat_pydriller_metrics = csv_builder.flatten_pydriller_metrics(metrics)
    flat_pylint_metrics = csv_builder.flatten_pylint_metrics(code_aspects)

    with open('./test_out.json', 'w') as file:
        json.dump(flat_pydriller_metrics, file, indent=4)
        csv_builder.write_pydriller_metrics_to_csv(flat_pydriller_metrics)

    with open('./test_code_aspects.json', 'w') as file:
        json.dump(flat_pylint_metrics, file, indent=4, cls=CustomEncoder)
        csv_builder.write_pylint_metrics_to_csv(flat_pylint_metrics)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()
