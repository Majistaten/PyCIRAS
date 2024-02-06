import datetime
import pathlib
import logging
from collections import ChainMap
from pydriller import Repository
from pydriller.metrics.process.change_set import ChangeSet
from pydriller.metrics.process.code_churn import CodeChurn
from pydriller.metrics.process.contributors_count import ContributorsCount
from pydriller.metrics.process.contributors_experience import ContributorsExperience
from pydriller.metrics.process.hunks_count import HunksCount
from pydriller.metrics.process.lines_count import LinesCount

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def _get_repositories(repositories: dict[str, str], clone_repo_to: str) -> dict[str, Repository]:
    base_path = pathlib.Path(clone_repo_to).absolute()

    if not base_path.exists():
        base_path.mkdir(parents=True)
    return {repo_name: _get_repository(repo_address, repo_name, clone_repo_to) for (repo_name, repo_address) in repositories.items()}

def _get_repository(repo_address: str, repo_name, clone_repo_to: str) -> Repository:
    repo_path = pathlib.Path(clone_repo_to + repo_name)

    if not repo_path.exists():
        return Repository(repo_address, clone_repo_to=clone_repo_to)
    return Repository(repo_path)

def _get_metrics(repo: Repository) -> dict[str, float]:
    """Extract various metrics from a repository."""
    metrics = {
        "total_commits": 0,
        "developers": set(),
        "lines_added": 0,
        "lines_deleted": 0,
        "files_modified": 0,
    }

    for commit in repo.traverse_commits():
        metrics["total_commits"] += 1
        metrics["developers"].add(commit.author.name)
        metrics["files_modified"] += len(commit.modified_files)
        for file in commit.modified_files:
            metrics["lines_added"] += file.added_lines
            metrics["lines_deleted"] += file.deleted_lines

    metrics["developers"] = len(metrics["developers"])
    metrics["average_lines_added_per_commit"] = metrics["lines_added"] / metrics["total_commits"]
    metrics["average_lines_deleted_per_commit"] = metrics["lines_deleted"] / metrics["total_commits"]

    return metrics

def _extract_process_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    metrics = {
        'change_set_max': 0,
        'change_set_avg': 0,
        'code_churn': {},
        'commits_count': {},
        'contributors_count': {'total': 0, 'minor': 0},
        'contributors_experience': {},
        'hunks_count': {},
        'lines_count': {'added': 0, 'removed': 0}
    }

    metrics['lines_count']['added'], metrics['lines_count']['removed'] = lines_count_metrics(repo_path, from_commit, to_commit, since, to, metrics)
    metrics['hunks_count'] = hunk_count_metrics(repo_path, from_commit, to_commit, since, to, metrics)
    metrics['contributors_experience'] = contribution_experience_metrics(repo_path, from_commit, to_commit, since, to, metrics)
    metrics['contributors_count']['total'], metrics['contributors_count']['minor'] = contribution_count_metrics(repo_path, from_commit, to_commit, since, to, metrics)
    metrics['code_churns'] = code_churns_metrics(repo_path, from_commit, to_commit, since, to, metrics)
    metrics['change_set_max'], metrics['change_set_avg'] = change_set_metrics(repo_path, from_commit, to_commit, since, to, metrics)

    return metrics

def lines_count_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    lines_count_metric = LinesCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    return lines_count_metric.count_added(), lines_count_metric.count_removed()

def hunk_count_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    hunks_count_metric = HunksCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    return hunks_count_metric.count()

def contribution_experience_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    contributors_experience_metric = ContributorsExperience(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    return contributors_experience_metric.count()

def contribution_count_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    contributors_count_metric = ContributorsCount(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    return contributors_count_metric.count(), contributors_count_metric.count_minor()

def code_churns_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    code_churn_metric = CodeChurn(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    metrics = {}
    metrics['total'] = code_churn_metric.count()
    metrics['max'] = code_churn_metric.max()
    metrics['avg'] = code_churn_metric.avg()
    return metrics

def change_set_metrics(repo_path: str, from_commit: str = None, to_commit: str = None, since: datetime = None, to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=repo_path, from_commit=from_commit, to_commit=to_commit, since=since, to=to)
    return change_set_metric.max(), change_set_metric.avg()



def process_repositories(repositories: list[str], clone_repo_to="./repos") -> dict[str, dict[str, float]]:
    # TODO: clean input, make sure there are no trailing and no /
    metrics = {}
    repos = _get_repositories(repositories, clone_repo_to)

    for repo in repos:
        metrics[repo] = ChainMap(_get_metrics(repo), _extract_process_metrics(repo))


    return metrics

