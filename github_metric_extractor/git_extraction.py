import pathlib
import logging
from tqdm import tqdm
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pydriller import Repository
from pydriller.metrics.process.change_set import ChangeSet
from pydriller.metrics.process.code_churn import CodeChurn
from pydriller.metrics.process.contributors_count import ContributorsCount
from pydriller.metrics.process.contributors_experience import ContributorsExperience
from pydriller.metrics.process.hunks_count import HunksCount
from pydriller.metrics.process.lines_count import LinesCount
import util

default_repository_path = '../repositories/'


# TODO make a method that returns commit hash + date from a repository


def mine_pydriller_metrics(repositories: list[str],
                           repository_directory: str = default_repository_path,
                           since: datetime = datetime.now(),
                           to: datetime = datetime.now() - relativedelta(years=20)
                           ) -> dict[str, dict[str, float]]:
    """Get Pydriller metrics from a git repository stored in a dict"""

    metrics = {}
    repos = _load_repositories(repositories, repository_directory)
    for address, repo in repos.items():
        repo_name = util.get_repo_name_from_url(address)
        metrics[repo_name] = _extract_commit_metrics(repo)
        metrics[repo_name].update(
            _extract_process_metrics(repo_path=repository_directory + '/' + repo_name, since=since, to=to))
        metrics[repo_name]['repository_name'] = repo_name
        metrics[repo_name]['repository_address'] = address

    return metrics


def get_commit_dates(repositories: list[str], repository_directory: str = default_repository_path) -> dict[str, any]:
    """Extract commit hash and dates from a list of repositories"""
    repos = _load_repositories(repositories)
    commit_dates = {}
    for address, repo in repos.items():
        hash_dates = []
        for commit in repo.traverse_commits():
            hash_dates.append({'commit_hash': commit.hash, 'date': commit.committer_date})
        commit_dates[address] = hash_dates

    return commit_dates


def _load_repositories(repositories: list[str], repository_directory: str = default_repository_path) -> (
        dict[str, Repository]):
    """Load repositories for further processing"""

    repository_path = pathlib.Path(repository_directory).absolute()
    repository_path.mkdir(parents=True, exist_ok=True)
    logging.debug('Loading repositories.')

    return {
        repo_url: _load_repository(repo_url, repository_directory) for repo_url in tqdm(repositories, desc="Loading Repositories")}


def _load_repository(repo_url: str, repository_directory: str = default_repository_path) -> Repository:
    """Load repository stored locally, or clone and load if not present"""

    repo_name = util.get_repo_name_from_url(repo_url)
    repo_path = pathlib.Path(repository_directory + repo_name)

    if not repo_path.exists():
        return Repository(repo_url, clone_repo_to=repository_directory)

    return Repository(str(repo_path))


def _extract_commit_metrics(repo: Repository) -> dict[str, float]:
    """Extract Pydriller commit metrics from a repository."""
    metrics = {
        "total_commits": 0,
        "developers": [],
        "developer_count": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "files_modified": 0,
    }

    for commit in tqdm(repo.traverse_commits(),
                       desc="Traversing commits, extracting Pydriller commit metrics",
                       ncols=100,
                       colour="blue"):
        metrics["total_commits"] += 1
        if commit.author.name not in metrics["developers"]:
            metrics["developers"].append(commit.author.name)
        metrics["files_modified"] += len(commit.modified_files)

        for file in commit.modified_files:
            metrics["lines_added"] += file.added_lines
            metrics["lines_deleted"] += file.deleted_lines

    metrics["developer_count"] = len(metrics["developers"])
    metrics["average_lines_added_per_commit"] = metrics["lines_added"] / metrics["total_commits"]
    metrics["average_lines_deleted_per_commit"] = metrics["lines_deleted"] / metrics["total_commits"]

    return metrics


def _extract_process_metrics(repo_path: str,
                             from_commit: str = None,
                             to_commit: str = None,
                             since: datetime = None,
                             to: datetime = None):
    """Extract Pydriller Process metrics from a repository"""

    metrics = {
        'change_set_max': 0,
        'change_set_avg': 0,
        'code_churn': {},
        'contributors_count': {'total': 0, 'minor': 0},
        'contributors_experience': {},
        'hunks_count': {},
        'lines_count': {'added': 0, 'removed': 0}
    }

    metrics['lines_count']['added'], metrics['lines_count']['removed'] = _lines_count_metrics(repo_path, from_commit,
                                                                                              to_commit, since, to)
    metrics['hunks_count'] = _hunk_count_metrics(repo_path, from_commit, to_commit, since, to)
    metrics['contributors_experience'] = _contribution_experience_metrics(repo_path, from_commit, to_commit, since, to)
    metrics['contributors_count']['total'], metrics['contributors_count']['minor'] = _contribution_count_metrics(
        repo_path, from_commit, to_commit, since, to)
    metrics['code_churn'] = _code_churns_metrics(repo_path, from_commit, to_commit, since, to)
    metrics['change_set_max'], metrics['change_set_avg'] = _change_set_metrics(repo_path, from_commit, to_commit, since,
                                                                               to)

    return metrics


def _lines_count_metrics(repo_path: str,
                         from_commit: str = None,
                         to_commit: str = None,
                         since: datetime = None,
                         to: datetime = None):
    lines_count_metric = LinesCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since,
                                    to=to)
    return lines_count_metric.count_added(), lines_count_metric.count_removed()


def _hunk_count_metrics(repo_path: str,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    hunks_count_metric = HunksCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since,
                                    to=to)
    return hunks_count_metric.count()


def _contribution_experience_metrics(repo_path: str,
                                     from_commit: str = None,
                                     to_commit: str = None,
                                     since: datetime = None,
                                     to: datetime = None):
    contributors_experience_metric = ContributorsExperience(path_to_repo=repo_path, from_commit=from_commit,
                                                            to_commit=to_commit, since=since, to=to)
    return contributors_experience_metric.count()


def _contribution_count_metrics(repo_path: str,
                                from_commit: str = None,
                                to_commit: str = None,
                                since: datetime = None,
                                to: datetime = None):
    contributors_count_metric = ContributorsCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit,
                                                  since=since, to=to)
    return contributors_count_metric.count(), contributors_count_metric.count_minor()


def _code_churns_metrics(repo_path: str,
                         from_commit: str = None,
                         to_commit: str = None,
                         since: datetime = None,
                         to: datetime = None):
    code_churn_metric = CodeChurn(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since,
                                  to=to)
    metrics = {'total': code_churn_metric.count(), 'max': code_churn_metric.max(), 'avg': code_churn_metric.avg()}
    return metrics


def _change_set_metrics(repo_path: str,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since,
                                  to=to)
    return change_set_metric.max(), change_set_metric.avg()


if __name__ == '__main__':
    """Test script for extracting Pydriller metrics"""
    logging.basicConfig(level=logging.INFO)
    with open('../repos.txt', 'r') as repo_file:
        links = [line.strip() for line in repo_file.readlines()]
        result = mine_pydriller_metrics(links, repository_directory="../repositories")

    print(result)
    with open('./test_out.txt', 'w') as file:
        for k, v in result.items():
            file.write(f'\n------------------------------------------------------\n')
            for key, value in v.items():
                file.write(str(key))
                file.write(' ----> ' + str(value) + '\n')
