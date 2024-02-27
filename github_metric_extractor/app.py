import repository_downloader
import git_extraction
import logging
import json
import pprint
import code_aspect_analyzer


def main():
    repository_paths = repository_downloader.download_repositories(repo_url_file='../repos.txt',
                                                                   destination_folder='../repositories')

    metrics = git_extraction.process_repositories(repository_paths, clone_repo_to="../repositories")
    with open('./test_out.json', 'w') as file:
        json.dump(metrics, file, indent=4)
    with open('./test_out.out', 'w') as file:
        pprint.pprint(metrics, file, indent=2, width=1)

    repo_commits = {v["repository_address"]: v["commits"] for (_, v) in metrics.items()}

    code_aspects = code_aspect_analyzer.analyze_repositories_commits(repo_commits)
    with open('./code_aspects.json', 'w') as file:
        json.dump(metrics, file, indent=4)
    with open('./code_aspects.out', 'w') as file:
        pprint.pprint(code_aspects, file, indent=2, width=1)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()

