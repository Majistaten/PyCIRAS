import logging
from datetime import datetime, timezone
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
from zoneinfo import ZoneInfo

from utility.progress_bars import RichIterableProgressBar


def mine_pydriller_metrics(repositories: list[str],
                           repository_directory: Path,
                           since: datetime = datetime.now(),
                           to: datetime = datetime.now() - relativedelta(years=20)
                           ) -> dict[str, dict[str, any]]:
    """Get Pydriller metrics in a dict from a git repository"""

    metrics = {}
    repos = _load_repositories(repositories, repository_directory)
    for repo_url, repo in repos.items():
        repo_name = util.get_repo_name_from_url(repo_url)
        metrics[repo_name] = _extract_commit_metrics(repo)
        metrics[repo_name].update(
            _extract_process_metrics(repo_path=repository_directory / repo_name, since=since, to=to))
        metrics[repo_name]['repository_name'] = repo_name
        metrics[repo_name]['repository_address'] = repo_url

    return metrics


def mine_stargazers_metrics(repo_urls: list[str]) -> dict[str, [dict]]:
    """Get stargazers metrics in a dict from the GraphQL API of GitHub"""

    load_dotenv()
    headers = {'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}'}
    metrics = {}

    for url in RichIterableProgressBar(
            repo_urls,
            description="Querying GraphQL API for Stargazers data",
            disable=config.DISABLE_PROGRESS_BARS):
        repo_owner = util.get_repo_owner_from_url(url)
        repo_name = util.get_repo_name_from_url(url)
        if check_stargazers_ratelimit()[0] == 0:
            logging.error(f"Ratelimit exceeded, skipping {repo_owner}/{repo_name}")
            continue
        stargazers_list = []
        end_cursor = None
        stargazers_data = None
        while True:
            json_query = {
                "query": f"""query {{
                    repository(owner: "{repo_owner}", name: "{repo_name}") {{
                        stargazers(first: 100{', after: "' + end_cursor + '"' if end_cursor else ''}) {{
                            edges {{
                                cursor
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
            if "message" in stargazers_data and stargazers_data["message"] == "Bad credentials":
                raise ValueError(f"The github API key may be invalid: {stargazers_data['message']}")
            elif "errors" in stargazers_data:
                logging.error(stargazers_data["errors"][0]["message"])
                continue
            edges = stargazers_data["data"]["repository"]["stargazers"]["edges"]
            if not edges:
                break
            stargazers_list.extend(edges)
            end_cursor = edges[-1]["cursor"]

            remaining, reset_at = check_stargazers_ratelimit()
            if remaining in [250, 100, 10, 1]:
                send_low_rate_limit_message(remaining, reset_at)
            elif remaining <= 0:
                break

        stargazers_data["data"]["repository"]["name"] = repo_name
        stargazers_data["data"]["repository"]["stargazers"]["edges"] = stargazers_list
        metrics[repo_name] = stargazers_data

    return metrics


def check_stargazers_ratelimit() -> tuple[int, datetime]:
    """ Checks the remaining calls to the GitHub api and returns the remaining amount and date of reset. """
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
    rate_limit_info = requests.post(config.GRAPHQL_API, json=rate_limiting_query, headers=headers).json()
    remaining = int(rate_limit_info['data']['rateLimit']['remaining'])
    reset_at_str = rate_limit_info['data']['rateLimit']['resetAt']
    reset_at = datetime.fromisoformat(reset_at_str.replace('Z', '')).replace(tzinfo=timezone.utc)

    return remaining, reset_at


def send_low_rate_limit_message(remaining: int, reset_at: datetime):
    message = f"The github api rate limit is getting low. You have {remaining} requests left and it will reset {reset_at.date()} {reset_at.time()}"
    title = "GitHub API rate limit"
    ntfyer.ntfy(message, title)
    logging.error(message)


def get_repository_lifespan(repo_url: str) -> dict[str, any]:
    """Get the first commit, last commit, and publish date of a project."""
    parts = repo_url.split("/")
    owner, repo = parts[-2], parts[-1]

    query = """
    query {
      repository(owner: "%s", name: "%s") {
        createdAt
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1) {
                edges {
                  node {
                    committedDate
                  }
                }
              }
              history(last: 1) {
                edges {
                  node {
                    committedDate
                  }
                }
              }
            }
          }
        }
      }
    }
    """ % (owner, repo)

    headers = {"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"}
    response = requests.post(config.GRAPHQL_API, json=query, headers=headers)

    if response.status_code == 200:
        data = response.json()['data']['repository']
        first_commit_date = data['defaultBranchRef']['target']['history']['edges'][0]['node']['committedDate']
        last_commit_date = data['defaultBranchRef']['target']['history']['edges'][-1]['node']['committedDate']
        publish_date = data['createdAt']

        result = {
            repo: {
                "first-commit": first_commit_date,
                "last-commit": last_commit_date,
                "publish-date": publish_date,
            }
        }
        return result
    else:
        logging.warning(f"Failed to fetch repository data. Status code: {response.status_code}")
        return {}


def get_repos_commit_metadata(repositories: list[str], repository_directory: Path) -> dict[str, any]:
    """Get a dictionary of repo urls with their commit hashes and dates of these commits from a list of repository
    paths """
    repos = _load_repositories(repositories, repository_directory)
    commit_dates = {}
    for repo_path, repo in repos.items():
        hash_dates = []
        for commit in repo.traverse_commits():
            hash_dates.append({'commit_hash': commit.hash, 'date': commit.committer_date})
        commit_dates[repo_path] = hash_dates

    return commit_dates


def _load_repositories(repositories: list[str], repository_directory: Path) -> (
        dict[str, Repository]):
    """Load repositories for further processing"""
    repository_path = repository_directory
    repository_path.mkdir(parents=True, exist_ok=True)
    logging.debug('Loading repositories.')

    return {
        str(repo_url): _load_repository(repo_url, repository_directory) for repo_url in
        RichIterableProgressBar(repositories,
                                description="Loading Repositories", # TODO ta bort denna progress bar
                                disable=config.DISABLE_PROGRESS_BARS)}


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
    lines_count_metric = LinesCount(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit,
                                    since=since,
                                    to=to)
    return lines_count_metric.count_added(), lines_count_metric.count_removed()


def _hunk_count_metrics(repo_path: Path,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    hunks_count_metric = HunksCount(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit,
                                    since=since,
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
    contributors_count_metric = ContributorsCount(path_to_repo=str(repo_path), from_commit=from_commit,
                                                  to_commit=to_commit,
                                                  since=since, to=to)
    return contributors_count_metric.count(), contributors_count_metric.count_minor()


def _code_churns_metrics(repo_path: Path,
                         from_commit: str = None,
                         to_commit: str = None,
                         since: datetime = None,
                         to: datetime = None):
    code_churn_metric = CodeChurn(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit,
                                  since=since,
                                  to=to)
    metrics = {'total': code_churn_metric.count(), 'max': code_churn_metric.max(), 'avg': code_churn_metric.avg()}
    return metrics


def _change_set_metrics(repo_path: Path,
                        from_commit: str = None,
                        to_commit: str = None,
                        since: datetime = None,
                        to: datetime = None):
    change_set_metric = ChangeSet(path_to_repo=str(repo_path), from_commit=from_commit, to_commit=to_commit,
                                  since=since,
                                  to=to)
    return change_set_metric.max(), change_set_metric.avg()
