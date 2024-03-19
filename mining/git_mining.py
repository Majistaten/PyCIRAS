"""This module contains the functions to mine git data from a repository. It uses Pydriller to extract the data."""

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pydriller import Repository
from pydriller.metrics.process.change_set import ChangeSet
from pydriller.metrics.process.code_churn import CodeChurn
from pydriller.metrics.process.contributors_count import ContributorsCount
from pydriller.metrics.process.contributors_experience import ContributorsExperience
from pydriller.metrics.process.hunks_count import HunksCount
from pydriller.metrics.process.lines_count import LinesCount
from utility import util, config, ntfyer
from dotenv import load_dotenv
import os
import requests
from pathlib import Path
from rich.pretty import pprint
from utility.progress_bars import RichIterableProgressBar
import pandas as pd


def mine_git_data(repo_path: Path,
                  repos: list[str],
                  since: datetime = datetime.now(),
                  to: datetime = datetime.now() - relativedelta(years=20)) -> dict[str, dict[str, any]]:
    """Mine git data from a list of repositories and return a dictionary with the data"""

    data = {}
    repos = _load_repositories(repos, repo_path)
    for repo_url, repo in repos.items():
        repo_name = util.get_repo_name_from_url(repo_url)
        data[repo_name] = _extract_commit_metrics(repo)
        data[repo_name].update(_extract_process_metrics(repo_path / repo_name, since, to))
        data[repo_name]['repo'] = repo_name
        data[repo_name]['repo_url'] = repo_url

    return data


def mine_stargazers_data(repo_urls: list[str]) -> dict[str, [dict]]:
    """Mine stargazers data from a list of repositories and return a dictionary with the data"""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for url in RichIterableProgressBar(
            repo_urls,
            description="Querying GraphQL API for Stargazers data",
            disable=config.DISABLE_PROGRESS_BARS):

        repo_owner = util.get_repo_owner_from_url(url)
        repo_name = util.get_repo_name_from_url(url)

        if check_graphql_rate_limit()[0] == 0:
            logging.error(f"Ratelimit exceeded, skipping {repo_owner}/{repo_name}")
            continue

        stargazers = []
        end_cursor = None
        while True:

            query = {
                "query": """
                    query repository($owner: String!, $name: String!, $first: Int, $after: String) {
                        repository(owner: $owner, name: $name) {
                            stargazers(first: $first, after: $after) {
                                edges {
                                    cursor
                                    starredAt
                                    node {
                                        login
                                    }
                                }
                            }
                        }
                    }
                """,
                "variables": {
                    "owner": repo_owner,
                    "name": repo_name,
                    "first": 100,
                    "after": end_cursor if end_cursor else None
                }
            }

            response = requests.post(config.GRAPHQL_API, json=query, headers=headers).json()

            if "message" in response and response["message"] == "Bad credentials":
                logging.error(f"\nBad credentials when querying the GraphQL API for stargazers\n"
                              f"Skipping repo: {repo_owner}/{repo_name}")
                break

            elif "errors" in response:
                logging.error(f"\nError when when querying the GraphQL API for stargazers\n"
                              f"repo: {repo_owner}/{repo_name}"
                              f"Error message: {response['errors'][0]['message']}")
                continue

            edges = response["data"]["repository"]["stargazers"]["edges"]

            if not edges:
                break

            stargazers.extend(edges)
            end_cursor = edges[-1]["cursor"]

            remaining, reset_at = check_graphql_rate_limit()

            logging.info(f"Remaining GraphQL requests: {remaining}, reset at: {reset_at}")

            if remaining in [250, 100, 10, 1]:
                send_graphql_rate_limit_warning(remaining, reset_at)
            elif remaining <= 0:
                break

        response["data"]["repository"]["name"] = repo_name
        response["data"]["repository"]["stargazers"]["edges"] = stargazers
        data[repo_name] = response

    return data


def check_graphql_rate_limit() -> tuple[int, pd.Timestamp]:
    """Check the rate limit of the GraphQL API"""

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}

    rate_limiting_query = {
        "query": """query {
        rateLimit {
            limit
            cost
            remaining
            resetAt
        }
        }"""
    }

    response = requests.post(config.GRAPHQL_API, json=rate_limiting_query, headers=headers).json()
    remaining = int(response['data']['rateLimit']['remaining'])
    reset_at = pd.to_datetime(response['data']['rateLimit']['resetAt'], utc=True)

    return remaining, reset_at


def send_graphql_rate_limit_warning(remaining: int, reset_at: pd.Timestamp):
    """Send a warning if the rate limit of GraphQL is getting low"""
    message = f"You have {remaining} requests remaining. Reset at: {reset_at.date()} {reset_at.time()}"
    title = "GraphQL API Rate Limit Low"
    ntfyer.ntfy(message, title)
    logging.error(message)


def mine_repo_lifespans(repos: list[str]) -> dict[str, any]:
    """Mine the lifespan of a list of repositories and return a dictionary with the data."""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for repo_url in RichIterableProgressBar(repos,
                                            description="Mining repo lifespans",
                                            disable=config.DISABLE_PROGRESS_BARS):
        repo_owner = util.get_repo_owner_from_url(repo_url)
        repo_name = util.get_repo_name_from_url(repo_url)

        lifespan_query = {
            "query": """
                    query ($owner: String!, $repo: String!) {
                      repository(owner: $owner, name: $repo) {
                        createdAt
                        pushedAt
                      }
                    }
                    """,
            "variables": {
                "owner": repo_owner,
                "repo": repo_name
            }
        }

        response = requests.post(config.GRAPHQL_API, json=lifespan_query, headers=headers).json()

        data.update({
            repo_name: {
                "created_at": response['data']['repository']['createdAt'],
                "pushed_at": response['data']['repository']['pushedAt']
            }})

    return data


# TODO: Baka in i pipeline och skriv ut i fil.
def get_repos_commit_metadata(repo_directory: Path, repo_paths: list[Path]) -> dict[str, any]:
    """Get repo paths with commit hashes and dates"""
    repos = _load_repositories(repo_paths, repo_directory)
    commit_dates = {}
    for repo_path, repo in repos.items():
        hash_dates = []
        for commit in repo.traverse_commits():
            #TODO bryt ut och förenkla?
            hash_dates.append({'commit_hash': commit.hash, 'date': commit.committer_date})
        commit_dates[repo_path] = hash_dates

    pprint(commit_dates)

    return commit_dates


# TODO behöver hela URL om den ska klona, annars bara namnet
# TODO: Fixa docstring som förklarar functionalitet
# TODO är inte url, är både path och url (Path/String)
def _load_repositories(repo_paths_or_urls: list[Path | str],
                       repo_directory: Path) -> (dict[str, Repository]):
    """Load repositories for further processing"""
    repository_path = repo_directory  # TODO använder repo dir här
    repository_path.mkdir(parents=True, exist_ok=True)
    logging.debug('Loading repositories.')

    return {
        str(repo_path_or_url):
            _load_repository(repo_path_or_url, repo_directory) for repo_path_or_url in repo_paths_or_urls
    }


# TODO behöver hela URL om den ska klona, annars bara namnet
# TODO är inte url, är både path och url (Path/String)
def _load_repository(repo_url_or_path: str, repository_directory: Path) -> Repository:
    """Load repository stored locally, or clone and load if not present"""

    repo_name = util.get_repo_name_from_url(repo_url_or_path)
    repo_path = repository_directory / repo_name

    if not repo_path.exists():
        return Repository(repo_url_or_path, clone_repo_to=str(repository_directory))

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

    for commit in RichIterableProgressBar(repo.traverse_commits(),
                                          description="Traversing commits, extracting Pydriller commit metrics",
                                          disable=config.DISABLE_PROGRESS_BARS):
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


# TODO används from_commit, to_commit?
def _extract_process_metrics(repo_path: Path,
                             since: datetime = None,
                             to: datetime = None):
    """Extract Pydriller Process metrics from a repository"""

    lines_count_added, lines_count_removed = _lines_count_metrics(repo_path, since, to)
    hunks_count = _hunk_count_metrics(repo_path, since, to)
    contributors_experience = _contribution_experience_metrics(repo_path, since, to)
    contributors_count_total, contributors_count_minor = _contribution_count_metrics(repo_path, since, to)
    code_churn = _code_churns_metrics(repo_path, since, to)
    change_set_max, change_set_avg = _change_set_metrics(repo_path, since, to)

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
                         since: datetime = None,
                         to: datetime = None):
    lines_count_metric = LinesCount(path_to_repo=str(repo_path),
                                    since=since,
                                    to=to)
    return lines_count_metric.count_added(), lines_count_metric.count_removed()


def _hunk_count_metrics(repo_path: Path,
                        since: datetime = None,
                        to: datetime = None):
    hunks_count_metric = HunksCount(path_to_repo=str(repo_path),
                                    since=since,
                                    to=to)
    return hunks_count_metric.count()


def _contribution_experience_metrics(repo_path: Path,
                                     since: datetime = None,
                                     to: datetime = None):
    contributors_experience_metric = ContributorsExperience(path_to_repo=str(repo_path), since=since, to=to)
    return contributors_experience_metric.count()


def _contribution_count_metrics(repo_path: Path,
                                since: datetime = None,
                                to: datetime = None):
    contributors_count_metric = ContributorsCount(path_to_repo=str(repo_path),
                                                  since=since, to=to)
    return contributors_count_metric.count(), contributors_count_metric.count_minor()


def _code_churns_metrics(repo_path: Path,
                         since: datetime = None,
                         to: datetime = None):
    code_churn_metric = CodeChurn(path_to_repo=str(repo_path),
                                  since=since,
                                  to=to)
    metrics = {'total': code_churn_metric.count(), 'max': code_churn_metric.max(), 'avg': code_churn_metric.avg()}
    return metrics


def _change_set_metrics(repo_path: Path,
                        since: datetime = None,
                        to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=str(repo_path),
                                  since=since,
                                  to=to)
    return change_set_metric.max(), change_set_metric.avg()
