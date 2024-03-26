"""This module contains the functions to mine git data from a repository. It uses Pydriller to extract the data."""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from pydriller.metrics.process.change_set import ChangeSet
from pydriller.metrics.process.code_churn import CodeChurn
from pydriller.metrics.process.contributors_count import ContributorsCount
from pydriller.metrics.process.contributors_experience import ContributorsExperience
from pydriller.metrics.process.history_complexity import HistoryComplexity
from pydriller.metrics.process.hunks_count import HunksCount
from pydriller.metrics.process.lines_count import LinesCount
from rich.progress import Progress

from data_io import repo_management
from utility import config, ntfyer, util
from utility.progress_bars import IterableProgressWrapper, RepositoryWithProgress


def mine_git_data(repo_directory: Path,
                  repo_urls: list[str],
                  progress: Progress,
                  since: datetime = datetime.now() - relativedelta(years=20),
                  to: datetime = datetime.now()) -> dict[str, dict[str, any]]:
    """Mine git data from a list of repositories and return a dictionary with the data"""

    data = {}
    repo_urls = repo_management.load_repos(repo_directory, repo_urls, progress)
    for repo_url, repo in IterableProgressWrapper(repo_urls.items(),
                                                  progress,
                                                  description=f'Mining Git Data',
                                                  postfix="Repos"):
        repo_name = util.get_repo_name_from_url_or_path(repo_url)
        data[repo_name] = _mine_commit_data(repo, progress)
        data[repo_name].update(_mine_process_data(repo_directory / repo_name, since=since, to=to, progress=progress))
        data[repo_name]['repo'] = repo_name
        data[repo_name]['repo_url'] = repo_url

    return data


# TODO fundera på hur beräkningarna på verkas om man kör flera workers
def _mine_commit_data(repo: RepositoryWithProgress, progress: Progress) -> dict[str, any]:
    """Mine commit data from a repository."""

    data = {
        "total_commits": 0,
        "developers": [],
        "developer_count": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "files_modified": 0,
    }

    dmm_mloc_valid_changes = 0
    dmm_mcc_valid_changes = 0
    dmm_mnop_valid_changes = 0
    dmm_mloc_sum = 0
    dmm_mcc_sum = 0
    dmm_mnop_sum = 0
    for commit in IterableProgressWrapper(repo.traverse_commits(),  # TODO disable if multiprocessing or config
                                          progress,
                                          description=
                                          util.get_repo_name_from_url_or_path(repo._conf.get('path_to_repo')),
                                          postfix='Commits'):
        data["total_commits"] += 1
        data["files_modified"] += len(commit.modified_files)

        if commit.author.name not in data["developers"]:
            data["developers"].append(commit.author.name)

        for file in commit.modified_files:
            data["lines_added"] += file.added_lines
            data["lines_deleted"] += file.deleted_lines

        # TODO history complexity
        # TODO samla in DMM per commit

        if commit.dmm_unit_size:
            dmm_mloc_valid_changes += 1
            dmm_mloc_sum += commit.dmm_unit_size
        if commit.dmm_unit_complexity:
            dmm_mcc_valid_changes += 1
            dmm_mcc_sum += commit.dmm_unit_complexity
        if commit.dmm_unit_interfacing:
            dmm_mnop_valid_changes += 1
            dmm_mnop_sum += commit.dmm_unit_interfacing

    data["developer_count"] = len(data["developers"])

    # Averages for commit-based metrics
    data["average_lines_added_per_commit"] = data["lines_added"] / data["total_commits"]
    data["average_lines_deleted_per_commit"] = data["lines_deleted"] / data["total_commits"]
    data["average_files_modified_per_commit"] = data["files_modified"] / data["total_commits"]

    # Averages for DMM metrics
    data["average_dmm_method_lines_of_code"] = \
        dmm_mloc_sum / dmm_mloc_valid_changes if dmm_mloc_valid_changes > 0 else 'nan'
    data["average_dmm_method_cyclomatic_complexity"] = \
        dmm_mcc_sum / dmm_mcc_valid_changes if dmm_mcc_valid_changes > 0 else 'nan'
    data["average_dmm_method_number_of_parameters"] = \
        dmm_mnop_sum / dmm_mnop_valid_changes if dmm_mnop_valid_changes > 0 else 'nan'

    return data


def _mine_process_data(repo_path: Path,
                       since: datetime = None,
                       to: datetime = None,
                       progress: Progress = None) -> dict[str, any]:
    """Mine process data from a repository"""
    repo = util.get_repo_name_from_url_or_path(repo_path)

    task = progress.add_task(f'Processing lines: {repo}', total=6)
    lines_avg, lines_count = _lines_count(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing hunks: {repo}')
    hunks_avg, hunks_count = _hunks_count(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing contributors experience: {repo}')
    contributors_exp_avg, contributors_experience = _contributor_experience(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing contributors count: {repo}')
    contributors_avg, contributors_count = _contributor_count(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing code churn: {repo}')
    churn_avg, code_churn = _code_churn(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing change set: {repo}')
    change_set_max, change_set_avg = _change_set(repo_path, since, to)

    progress.update(task, advance=1, description=f'Processing history complexity: {repo}')
    history_avg, history_complexity = _history_complexity(repo_path, since, to)

    progress.stop_task(task)
    progress.remove_task(task)
    result = {
        'lines_count': lines_count,
        'hunks_count': hunks_count,
        'contributors_experience': contributors_experience,
        'contributors_count': contributors_count,
        'history_complexity': history_complexity,
        'code_churn': code_churn,
        'change_set_max': change_set_max,
        'change_set_avg': change_set_avg
    }
    result.update(lines_avg)
    result.update(hunks_avg)
    result.update(contributors_exp_avg)
    result.update(contributors_avg)
    result.update(churn_avg)
    result.update(history_avg)
    return result


def _lines_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine lines count data from a repository. The lines count is the number of lines added and removed in a file."""
    data = LinesCount(path_to_repo=str(repo_path), since=since, to=to)
    avg_lines_added = sum([lines for lines in data.count_added().values()]) / len(data.count_added())
    avg_lines_removed = sum([lines for lines in data.count_removed().values()]) / len(data.count_removed())
    avg_avg_lines_added = sum([lines for lines in data.avg_added().values()]) / len(data.avg_added())
    return ({
        'average_lines_added_to_files': avg_lines_added,
        'average_lines_deleted_from_files': avg_lines_removed,
        'average_avg_lines_added_to_files': avg_avg_lines_added},
            {
        'added': data.count_added(),
        'removed': data.count_removed(),
        'avg_added': data.avg_added()
            })


def _hunks_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """
    Mine hunks count data from a repository.
    The hunks count is the number of hunks (block of changes in a diff) made to a commit file.
    """
    data = HunksCount(path_to_repo=str(repo_path), since=since, to=to)
    avg_hunks = sum([hunks for hunks in data.count().values()]) / len(data.count())
    return {'average_hunks': avg_hunks}, data.count()


def _contributor_experience(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine contribution experience data from a repository. The experience is the percentage of lines authored by the
    highest contributor of a file."""
    data = ContributorsExperience(path_to_repo=str(repo_path), since=since, to=to)
    avg_contributor_experience = sum([experience for experience in data.count().values()]) / len(data.count())
    return {'average_contributor_experience': avg_contributor_experience}, data.count()


def _contributor_count(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine contribution count data from a repository. The count is the number of contributors to a file."""
    data = ContributorsCount(path_to_repo=str(repo_path), since=since, to=to)
    avg_contributors = sum([contributors for contributors in data.count().values()]) / len(data.count())
    avg_contributors_minor = sum([contributors for contributors in data.count_minor().values()]) / len(
        data.count_minor())
    return ({
        'average_contributors': avg_contributors,
        'average_minor_contributors': avg_contributors_minor},
            {
        'total': data.count(),
        'minor': data.count_minor()})


def _code_churn(repo_path: Path, since: datetime = None, to: datetime = None):
    """"
    Mine code churn data from a repository. The code churn is the number of lines added and removed in a commit.
    The code churn is either the sum of, or the difference between the added and removed lines.
    """
    data = CodeChurn(path_to_repo=str(repo_path), since=since, to=to)
    avg_code_churn_total = sum([churn for churn in data.count().values()]) / len(data.count())
    avg_code_churn_max = sum([churn for churn in data.max().values()]) / len(data.max())
    avg_code_churn_avg = sum([churn for churn in data.avg().values()]) / len(data.avg())
    return ({
        'average_code_churn_total': avg_code_churn_total,
        'average_code_churn_max': avg_code_churn_max,
        'average_code_churn_avg': avg_code_churn_avg},
            {
        'total': data.count(),
        'max': data.max(),
        'avg': data.avg()})


def _change_set(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine change set data from a repository. The change set if files committed together in a commit."""
    change_set_metric = ChangeSet(path_to_repo=str(repo_path), since=since, to=to)
    return change_set_metric.max(), change_set_metric.avg()


# TODO: Make sure this works as intended, not included in the documentation
def _history_complexity(repo_path: Path, since: datetime = None, to: datetime = None):
    """Mine history complexity data from a repository"""
    data = HistoryComplexity(path_to_repo=str(repo_path), since=since, to=to)
    avg_history_complexity = sum([complexity for complexity in data.count().values()]) / len(data.count())
    return {'average_history_complexity': avg_history_complexity}, data.count()


def mine_stargazers_data(repo_urls: list[str], progress: Progress) -> dict[str, [dict]]:
    """Mine stargazers data from a list of repositories and return a dictionary with the data"""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for url in IterableProgressWrapper(repo_urls, progress, "Querying GraphQL API for Stargazers", postfix="Repos"):

        repo_owner = util.get_repo_owner_from_url(url)
        repo_name = util.get_repo_name_from_url_or_path(url)

        if _check_graphql_rate_limit()[0] == 0:
            logging.error(f"Ratelimit exceeded, skipping {repo_owner}/{repo_name}")
            continue

        stargazers = []
        end_cursor = None

        query_task = progress.add_task(f'{util.get_repo_name_from_url_or_path(url)}', total=None)
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

        progress.stop_task(query_task)
        progress.remove_task(query_task)

        response["data"]["repository"]["name"] = repo_name
        response["data"]["repository"]["stargazers"]["edges"] = stargazers
        data[repo_name] = response

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


def mine_repo_metadata(repos: list[str], progress: Progress) -> dict[str, any]:
    """Mine the metadata of a list of repositories and return a dictionary with the data."""

    load_dotenv()

    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    data = {}
    for repo_url in IterableProgressWrapper(repos,
                                            progress,
                                            description="Querying GraphQL API for metadata",
                                            postfix='Repos'):

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


def _send_graphql_rate_limit_warning(remaining: int, reset_at: pd.Timestamp):
    """Send a warning if the rate limit of GraphQL is getting low"""
    message = f"You have {remaining} requests remaining. Reset at: {reset_at.date()} {reset_at.time()}"
    title = "GraphQL API Rate Limit Low"
    ntfyer.ntfy(message, title)
    logging.error(message)
