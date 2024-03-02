from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.reporters.ureports.nodes import Section
from pylint.message import Message
from io import StringIO
import logging
from tqdm import tqdm
from git import Repo
from utility import util


# TODO kolla om vi ska enabla optional plugins för att maximera inhämtningen
#  https://pylint.pycqa.org/en/latest/user_guide/checkers/extensions.html

class LintReporter(TextReporter):
    """Custom Pylint reporter, collects linting messages and allows for further processing"""

    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages: list[Message] = []

    def _display(self, layout: Section):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def mine_pylint_metrics(repositories_with_commits: dict[str, any]) -> dict[str, any]:
    """Get Pylint metrics from the commits of multiple git repositories"""
    metrics = {}
    for repository, commits in repositories_with_commits.items():
        logging.info(f"repository {repository}")
        metrics[repository] = _extract_pylint_metrics(repository, commits)
    return metrics


def _extract_pylint_metrics(repository_path: str, commits: any) -> dict[str, any]:
    """Extract Pylint metrics from a the commits of a single repository"""
    metrics = {}
    repo = Repo(repository_path)
    for commit in tqdm(commits,
                       desc=f"Traversing commits, extracting pylint metrics",
                       postfix=util.get_repo_name_from_path(repository_path),
                       ncols=150,
                       colour="blue"):
        commit_hash = commit["commit_hash"]
        date = commit["date"]
        repo.git.checkout(commit_hash)
        metrics[commit_hash] = _run_pylint(repository_path)
        if metrics[commit_hash] is not None:
            metrics[commit_hash]['date'] = date
    return metrics


def _run_pylint(repository_path: str) -> dict[str, any] | None:
    """Execute Pylint on a single repository, get the report in a dict"""
    result = {}
    target_files = util.get_python_files_from_directory(repository_path)
    if target_files is None or len(target_files) == 0:
        logging.info(f"No python files found in {repository_path}")
        return None

    out = StringIO()
    reporter = LintReporter(output=out)

    logging.info(f"Analyzing {len(target_files)} files in {repository_path}")

    run = Run(target_files, reporter=reporter, exit=False)
    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {str(attr): getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    repository_name = util.get_repo_name_from_path(repository_path)
    result['messages'] = _parse_pylint_messages(reporter.messages)
    result['messages']['repository_name'] = repository_name
    result['stats'] = stats_dict
    result['stats']['repository_name'] = repository_name

    logging.info(f"Analyzed {len(target_files)} files in {repository_path}")

    return result


def _parse_pylint_messages(messages: list[Message]) -> dict[str, any]:
    """Parses Pylint Messages and returns them in a formatted dictionary using strings"""

    logging.info(f"Extracting messages from {len(messages)} messages")

    result = {}
    for msg in messages:
        module = msg.module
        if module not in result:
            result[module] = {'total_messages': 0, 'categories': {}}

        category = msg.category
        if category not in result[module]['categories']:
            result[module]['categories'][category] = {'total': 0, 'message_ids': {}}

        msg_id = msg.msg_id
        if msg_id not in result[module]['categories'][category]['message_ids']:
            result[module]['categories'][category]['message_ids'][msg_id] = {
                'count': 0,
                'symbol': msg.symbol
            }

        result[module]['total_messages'] += 1
        result[module]['categories'][category]['total'] += 1
        result[module]['categories'][category]['message_ids'][msg_id]['count'] += 1

    logging.info(f"Extracted {len(result)} modules")

    return result


if __name__ == '__main__':
    """"Test script for analyzing repositories"""
    pass
