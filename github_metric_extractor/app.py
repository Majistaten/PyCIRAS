import repository_downloader
import git_extraction
import logging
import pprint
import code_aspect_analyzer


def main():
    repository_paths = repository_downloader.download_repositories(repo_url_file='../repos.txt',
                                                                   destination_folder='../repositories')
    # print(repository_paths)
    metrics = git_extraction.process_repositories(repository_paths, clone_repo_to="../repositories")
    with open('./test_out.out', 'w') as file:
        for k, v in metrics.items():
            file.write(f'\n------------------------------------------------------\n')
            for key, value in v.items():
                file.write(str(key))
                file.write(' ----> ' + str(value) + '\n')
    # code_aspects = code_aspect_analyzer.analyze_repositories(repository_paths)

    repo_commits = {v["repository_address"]: v["commits"] for (_, v) in metrics.items()}

    code_aspects = code_aspect_analyzer.analyze_repositories_commits(repo_commits)

    with open('./code_aspects.out', 'w') as file:
        for k, v in code_aspects.items():
            file.write(f'\n------------------------------------------------------\n')
            for key, value in v.items():
                file.write(str(key))
                file.write(' ----> ' + str(value) + '\n')


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()

