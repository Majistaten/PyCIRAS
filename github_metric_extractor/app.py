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
    with open('./test_out.txt', 'w') as file:
        for k, v in metrics.items():
            file.write(f'\n------------------------------------------------------\n')
            for key, value in v.items():
                file.write(str(key))
                file.write(' ----> ' + str(value) + '\n')
    # pprint.pprint(metrics, width=200)
    code_aspects = code_aspect_analyzer.analyze_repositories(repository_paths)
    with open('./code_aspects.txt', 'w') as file:
        for k, v in code_aspects.items():
            file.write(f'\n------------------------------------------------------\n')
            for key, value in v.items():
                file.write(str(key))
                file.write(' ----> ' + str(value) + '\n')
    # pprint.pprint(code_aspects, width=200)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()

