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
from utility.progress_bars import RichIterableProgressBar
import pandas as pd
from data_io import repo_management
from rich.pretty import pprint


def mine_git_data(repo_directory: Path,
                  repo_urls: list[str],
                  since: datetime = datetime.now(),
                  to: datetime = datetime.now() - relativedelta(years=20)) -> dict[str, dict[str, any]]:
    """Mine git data from a list of repositories and return a dictionary with the data"""

    data = {}
    repo_urls = repo_management.load_repos(repo_directory, repo_urls)
    for repo_url, repo in repo_urls.items():
        repo_name = util.get_repo_name_from_url_or_path(repo_url)
        data[repo_name] = _mine_commit_data(repo)
        data[repo_name].update(_mine_process_data(repo_directory / repo_name, since, to))
        data[repo_name]['repo'] = repo_name
        data[repo_name]['repo_url'] = repo_url

    return data


def _mine_commit_data(repo: Repository) -> dict[str, any]:
    """Mine commit data from a repository."""

    data = {
        "total_commits": 0,
        "developers": [],
        "developer_count": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "files_modified": 0,
    }

    for commit in RichIterableProgressBar(repo.traverse_commits(),
                                          description="Traversing commits, mining git data",
                                          disable=config.DISABLE_PROGRESS_BARS):

        data["total_commits"] += 1
        data["files_modified"] += len(commit.modified_files)

        if commit.author.name not in data["developers"]:
            data["developers"].append(commit.author.name)

        for file in commit.modified_files:
            data["lines_added"] += file.added_lines
            data["lines_deleted"] += file.deleted_lines

    data["developer_count"] = len(data["developers"])
    data["average_lines_added_per_commit"] = data["lines_added"] / data["total_commits"]
    data["average_lines_deleted_per_commit"] = data["lines_deleted"] / data["total_commits"]

    return data


def _mine_process_data(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine process data from a repository"""

    lines_count_added, lines_count_removed = _lines_count(repo_path, since, to)
    hunks_count = _hunks_count(repo_path, since, to)
    contributors_experience = _contributor_experience(repo_path, since, to)
    contributors_count_total, contributors_count_minor = _contributor_count(repo_path, since, to)
    code_churn = _code_churn(repo_path, since, to)
    change_set_max, change_set_avg = _change_set(repo_path, since, to)

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


def _lines_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine lines count data from a repository"""
    data = LinesCount(path_to_repo=str(repo_path), since=since, to=to)
    return data.count_added(), data.count_removed()


def _hunks_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine hunks count data from a repository"""
    data = HunksCount(path_to_repo=str(repo_path), since=since, to=to)
    return data.count()


def _contributor_experience(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine contribution experience data from a repository"""
    data = ContributorsExperience(path_to_repo=str(repo_path), since=since, to=to)
    return data.count()


def _contributor_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine contribution count data from a repository"""
    data = ContributorsCount(path_to_repo=str(repo_path), since=since, to=to)
    return data.count(), data.count_minor()


def _code_churn(repo_path: Path, since: datetime = None, to: datetime = None):
    """"Mine code churn data from a repository"""
    data = CodeChurn(path_to_repo=str(repo_path), since=since, to=to)
    return {'total': data.count(), 'max': data.max(), 'avg': data.avg()}


def _change_set(repo_path: Path, since: datetime = None, to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=str(repo_path), since=since, to=to)
    return change_set_metric.max(), change_set_metric.avg()


def mine_stargazers_data(repo_urls: list[str]) -> dict[str, [dict]]:
    """Mine stargazers data from a list of repositories and return a dictionary with the data"""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for url in RichIterableProgressBar(
            repo_urls,
            description="Querying GraphQL API for stargazers data",
            disable=config.DISABLE_PROGRESS_BARS):

        repo_owner = util.get_repo_owner_from_url(url)
        repo_name = util.get_repo_name_from_url_or_path(url)

        if _check_graphql_rate_limit()[0] == 0:
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

            remaining, reset_at = _check_graphql_rate_limit()

            logging.debug(f"Remaining GraphQL requests: {remaining}, reset at: {reset_at}")

            if remaining in [250, 100, 10, 1]:
                _send_graphql_rate_limit_warning(remaining, reset_at)
            elif remaining <= 0:
                break

        response["data"]["repository"]["name"] = repo_name
        response["data"]["repository"]["stargazers"]["edges"] = stargazers
        data[repo_name] = response

    return data


def mine_repo_metadata(repos: list[str]) -> dict[str, any]:
    """Mine the metadata of a list of repositories and return a dictionary with the data."""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for repo_url in RichIterableProgressBar(repos,
                                            description="Querying GraphQL API for repo metadata",
                                            disable=config.DISABLE_PROGRESS_BARS):
        repo_owner = util.get_repo_owner_from_url(repo_url)
        repo_name = util.get_repo_name_from_url_or_path(repo_url)

        query = {
            "query": """
                    query ($owner: String!, $repo: String!) {
                      repository(owner: $owner, name: $repo) {
                        createdAt
                        pushedAt
                        updatedAt
                        archivedAt
                        description
                        forkCount
                        stargazerCount
                        hasDiscussionsEnabled
                        hasIssuesEnabled
                        hasProjectsEnabled
                        hasSponsorshipsEnabled
                        fundingLinks {
                            platform
                        }
                        hasWikiEnabled
                        homepageUrl
                        isArchived
                        isEmpty
                        isFork
                        isInOrganization
                        isLocked
                        isMirror
                        isPrivate
                        isTemplate
                        licenseInfo {
                            name
                            body
                            description
                        }
                        lockReason
                        visibility
                        url
                        owner {
                            login
                        }
                        resourcePath
                        diskUsage
                        languages(first: 10) {
                            nodes { 
                                name
                            }
                        }
                        primaryLanguage {
                            name
                        }
                      }
                    }
                    """,
            "variables": {
                "owner": repo_owner,
                "repo": repo_name
            }
        }

        response = requests.post(config.GRAPHQL_API, json=query, headers=headers).json()

        if "errors" in response:
            logging.error(f"\nError when when querying GraphQL API for repo metadata\n"
                          f"repo: {repo_owner}/{repo_name}"
                          f"Error message: {response['errors'][0]['message']}")
            continue

        metadata = response['data']['repository']

        data.update({
            repo_name: metadata
        })

        remaining, reset_at = _check_graphql_rate_limit()

        logging.debug(f"Remaining GraphQL requests: {remaining}, reset at: {reset_at}")

        if remaining in [250, 100, 10, 1]:
            _send_graphql_rate_limit_warning(remaining, reset_at)
        elif remaining <= 0:
            break

    return data


def _check_graphql_rate_limit() -> tuple[int, pd.Timestamp]:
    """Check the rate limit of the GraphQL API"""

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}

    query = {
        "query": """query {
        rateLimit {
            limit
            cost
            remaining
            resetAt
        }
        }"""
    }

    response = requests.post(config.GRAPHQL_API, json=query, headers=headers).json()

    if "errors" in response:
        logging.error(f"\nError when when querying GraphQL API for rate limit info\n"
                      f"Error message: {response['errors'][0]['message']}")
        return 0, pd.to_datetime(datetime.now(), utc=True)

    remaining = int(response['data']['rateLimit']['remaining'])
    reset_at = pd.to_datetime(response['data']['rateLimit']['resetAt'], utc=True)

    return remaining, reset_at


def _send_graphql_rate_limit_warning(remaining: int, reset_at: pd.Timestamp):
    """Send a warning if the rate limit of GraphQL is getting low"""
    message = f"You have {remaining} requests remaining. Reset at: {reset_at.date()} {reset_at.time()}"
    title = "GraphQL API Rate Limit Low"
    ntfyer.ntfy(message, title)
    logging.error(message)
