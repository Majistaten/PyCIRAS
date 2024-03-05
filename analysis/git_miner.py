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
from utility import util, config
from dotenv import load_dotenv
import os
import requests
from datahandling import data_writer, data_converter
from pathlib import Path
import json


# TODO make a method that returns commit hash + date from a repository

# TODO try Pydrillers built in CSV creation

def mine_pydriller_metrics(repositories: list[str],
                           repository_directory: Path,
                           since: datetime = datetime.now(),
                           to: datetime = datetime.now() - relativedelta(years=20)
                           ) -> dict[str, dict[str, any]]:
    """Get Pydriller metrics in a dict from a git repository"""

    metrics = {}
    repos = _load_repositories(repositories, repository_directory)
    for address, repo in repos.items():
        repo_name = util.get_repo_name_from_url(address)
        metrics[repo_name] = _extract_commit_metrics(repo)
        metrics[repo_name].update(
            _extract_process_metrics(repo_path=repository_directory / repo_name, since=since, to=to))
        metrics[repo_name]['repository_name'] = repo_name
        metrics[repo_name]['repository_address'] = address

    return metrics


# TODO implementera pagination vid behov för att få ut alla stargazers utan att slå i rate limit/size limit
def mine_stargazers_metrics(repo_urls: list[str]) -> list[dict[any]]:
    """Get stargazers metrics in a dict from the GraphQL API of GitHub"""

    load_dotenv()
    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    metrics = []

    for url in tqdm(repo_urls,
                    desc="Querying GraphQL API for Stargazers data",
                    ncols=150):
        repo_owner = util.get_repo_owner_from_url(url)
        repo_name = util.get_repo_name_from_url(url)
        json_query = {
            "query": f"""query {{
                repository(owner: "{repo_owner}", name: "{repo_name}") {{
                    stargazers(first: 100) {{
                        edges {{
                            starredAt
                                node {{
                                    login
                                }}
                        }}
                    }}
                }}
            }}"""
        }
        stargazers_data = requests.post(config.GRAPHQL_API, json=json_query, headers=headers).json()
        stargazers_data["data"]["repository"]["name"] = repo_owner + "/" + repo_name
        metrics.append(stargazers_data)

        # TODO debug.warning om rate limit börjar bli för låg
        # TODO skapa funktion som sköter rate limit checking
        # rate_limiting_query = {
        #     "query": """query {
        #     rateLimit {
        #         limit
        #         cost
        #         remaining
        #         resetAt
        #     }
        #     }"""
        # }
        # rate_limit_info = requests.post(config.GRAPHQL_API, json=rate_limiting_query, headers=headers).json()
        # print(rate_limit_info)

    return metrics


def get_commit_dates(repositories: list[str], repository_directory: Path) -> dict[str, any]:
    """Extract commit hash and dates from a list of repositories"""
    repos = _load_repositories(repositories, repository_directory)
    commit_dates = {}
    for address, repo in repos.items():
        hash_dates = []
        for commit in repo.traverse_commits():
            hash_dates.append({'commit_hash': commit.hash, 'date': commit.committer_date})
        commit_dates[address] = hash_dates

    return commit_dates


def _load_repositories(repositories: list[str], repository_directory: Path) -> (
        dict[str, Repository]):
    """Load repositories for further processing"""

    repository_path = repository_directory
    repository_path.mkdir(parents=True, exist_ok=True)
    logging.debug('Loading repositories.')

    return {
        str(repo_url): _load_repository(repo_url, repository_directory) for repo_url in
        tqdm(repositories, desc="Loading Repositories", ncols=150)}


def _load_repository(repo_url: str, repository_directory: Path) -> Repository:
    """Load repository stored locally, or clone and load if not present"""

    repo_name = util.get_repo_name_from_url(repo_url)
    repo_path = repository_directory / repo_name

    if not repo_path.exists():
        return Repository(repo_url, clone_repo_to=str(repository_directory))

    return Repository(str(repo_path))


def _extract_commit_metrics(repo: Repository) -> dict[str, any]:
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
                       ncols=150,
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


def _extract_process_metrics(repo_path: Path,
                             from_commit: str = None,
                             to_commit: str = None,
                             since: datetime = None,
                             to: datetime = None):
    """Extract Pydriller Process metrics from a repository"""

    lines_count_added, lines_count_removed = _lines_count_metrics(repo_path, from_commit, to_commit, since, to)
    hunks_count = _hunk_count_metrics(repo_path, from_commit, to_commit, since, to)
    contributors_experience = _contribution_experience_metrics(repo_path, from_commit, to_commit, since, to)
    contributors_count_total, contributors_count_minor = _contribution_count_metrics(repo_path, from_commit, to_commit,
                                                                                     since, to)
    code_churn = _code_churns_metrics(repo_path, from_commit, to_commit, since, to)
    change_set_max, change_set_avg = _change_set_metrics(repo_path, from_commit, to_commit, since, to)

    return {
        'lines_count': {
            'added': lines_count_added,
            'removed': lines_count_removed
        },
        'hunks_count': hunks_count,
        'contributors_experience': contributors_experience,
        'contributors_count': {
            'total': contributors_count_total,
            'minor': contributors_count_minor
        },
        'code_churn': code_churn,
        'change_set_max': change_set_max,
        'change_set_avg': change_set_avg
    }


def _lines_count_metrics(repo_path: Path,
                         from_commit: str = None,
                         to_commit: str = None,
                         since: datetime = None,
                         to: datetime = None):
    lines_count_metric = LinesCount(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit, since=since,
                                    to=to)
    return lines_count_metric.count_added(), lines_count_metric.count_removed()


def _hunk_count_metrics(repo_path: Path,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    hunks_count_metric = HunksCount(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit, since=since,
                                    to=to)
    return hunks_count_metric.count()


def _contribution_experience_metrics(repo_path: Path,
                                     from_commit: str = None,
                                     to_commit: str = None,
                                     since: datetime = None,
                                     to: datetime = None):
    contributors_experience_metric = ContributorsExperience(path_to_repo=str(repo_path), from_commit=from_commit,
                                                            to_commit=to_commit, since=since, to=to)
    return contributors_experience_metric.count()


def _contribution_count_metrics(repo_path: Path,
                                from_commit: str = None,
                                to_commit: str = None,
                                since: datetime = None,
                                to: datetime = None):
    contributors_count_metric = ContributorsCount(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit,
                                                  since=since, to=to)
    return contributors_count_metric.count(), contributors_count_metric.count_minor()


def _code_churns_metrics(repo_path: Path,
                         from_commit: str = None,
                         to_commit: str = None,
                         since: datetime = None,
                         to: datetime = None):
    code_churn_metric = CodeChurn(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit, since=since,
                                  to=to)
    metrics = {'total': code_churn_metric.count(), 'max': code_churn_metric.max(), 'avg': code_churn_metric.avg()}
    return metrics


def _change_set_metrics(repo_path: Path,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit, since=since,
                                  to=to)
    return change_set_metric.max(), change_set_metric.avg()
