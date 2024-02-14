import argparse

from git import Repo
from pathlib import Path
from git.remote import RemoteProgress
import logging
from rich.progress import Progress


class CloneProgress(RemoteProgress):
    def __init__(self, progress):
        super().__init__()
        self.progress = progress
        self.task_id = None

    def update(self, op_code, cur_count, max_count=None, message=''):
        if self.task_id is None:
            self.task_id = self.progress.add_task("[cyan]Cloning...", total=max_count)
        self.progress.update(self.task_id, completed=cur_count, total=max_count)


def clone_repository(repo_url, destination_folder):
    try:
        path = Path(destination_folder)
        if not path.exists() or not path.is_dir():
            logging.warning('Path (' + destination_folder + ') did not exist, creating path.')
            path.mkdir(parents=True, exist_ok=True)

        logging.info('Cloning Git Repository: ' + repo_url + '...')
        with Progress() as progress:
            Repo.clone_from(repo_url, destination_folder + '/' + get_repo_name(repo_url), progress=CloneProgress(progress))

        logging.info('Git Repository cloned to ' + destination_folder)
        return True
    except Exception as ex:
        logging.error('Something went wrong!\n' + str(ex))
        return False


def download_repositories(repo_url_file, destination_folder):
    url_file = Path(repo_url_file)
    if not url_file.is_file():
        logging.error('The provided repository url file does not exist or is not a file.')
        return False
    with open(url_file, 'r') as file:
        logging.info('Downloading repositories from ' + url_file.name)
        for line in file:
            sanitized_line = sanitize_url(line)
            if clone_repository(sanitized_line, destination_folder):
                logging.info('Repository ' + sanitized_line + ' was cloned to ' + destination_folder)
        logging.info('Finished downloading repositories from ' + url_file.name)
    return True


def sanitize_url(url: str):
    sanitized_url = url.replace(' ', '')

    return sanitized_url


def get_repo_name(repo):
    repo_name = repo.split('/')[-1].replace('.git', '').replace('/', '')
    return repo_name


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo-url')
    parser.add_argument('-d', '--destination-folder')
    parser.add_argument('-f', '--url-file')
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)')
    try:
        if args.destination_folder is not None:
            if args.repo_url is not None:
                clone_repository(args.repo_url, args.destination_folder)
            if args.url_file is not None:
                download_repositories(args.url_file, args.destination_folder)
    except Exception as e:
        logging.error('Something went wrong.')

