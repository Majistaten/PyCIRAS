import logging
from datetime import datetime
from io import StringIO
from pathlib import Path

from git import Repo
from pylint.lint import Run
from pylint.message import Message
from pylint.reporters.text import TextReporter
from pylint.reporters.ureports.nodes import Section
from rich.progress import (
    Progress,
)

from utility import config, util
from utility.progress_bars import IterableProgressWrapper


class LintReporter(TextReporter):
    """Custom Pylint reporter, collects linting messages and allows for further processing"""

    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages: list[Message] = []

    def _display(self, layout: Section):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def mine_lint_data(repo_paths_with_commit_metadata: dict[str, list[tuple[str, datetime]]],
                   progress: Progress) -> dict[str, any]:
    """Mine lint data from the commits of multiple git repositories"""
    data = {}
    for repo_path, commit_metadata in IterableProgressWrapper(repo_paths_with_commit_metadata.items(),
                                                              progress,
                                                              description="Mining lint data",
                                                              postfix="Repos"):
        logging.info(f"Mining lint data: {repo_path}")
        data[util.get_repo_name_from_url_or_path(repo_path)] = _mine_commit_data(Path(repo_path),
                                                                                 commit_metadata,
                                                                                 progress)

    return data


def _mine_commit_data(repository_path: Path,
                      commit_metadata: [tuple[str, datetime]],
                      progress: Progress) -> dict[str, any]:
    """Mines lint data from the commits of a repository"""

    data = {}
    repo = Repo(repository_path)
    for commit_hash, date in IterableProgressWrapper(commit_metadata,
                                                     progress,
                                                     description=util.get_repo_name_from_url_or_path(repository_path),
                                                     postfix='Commits'):

        repo.git.checkout(commit_hash)
        lint_data = _run_pylint(repository_path, commit_hash)

        if lint_data is not None:
            data[commit_hash] = lint_data
            data[commit_hash]['date'] = date

    return data


def _run_pylint(repository_path: Path, commit: str) -> dict[str, any] | None:
    """Runs Pylint on Python files"""

    target_files = util.get_python_files_from_directory(repository_path)
    if target_files is None or len(target_files) == 0:
        logging.info(f"\nThis commit has no Python files\n"
                     f"Skipping commit: {commit}")
        return None
    elif len(target_files) > 1000:
        logging.warning(
            f"Found {len(target_files)} files in {repository_path}. "
            f"This might take a while, consider skipping this repository.")

    data = {}

    out = StringIO()
    reporter = LintReporter(output=out)

    logging.info(f'[{util.get_repo_name_from_url_or_path(repository_path)}]: {commit}\n'
                 f'Mining {len(target_files)} Python files')

    # TODO få ut logging från Pylint
    run = Run([f'--rcfile={config.PYLINT_CONFIG}'] + target_files, reporter=reporter, exit=False)
    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {str(attr): getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    repo_name = util.get_repo_name_from_url_or_path(str(repository_path))
    data['messages'] = _parse_pylint_messages(reporter.messages, commit)
    data['messages']['repository_name'] = repo_name
    data['stats'] = stats_dict
    data['stats']['avg_mccabe_complexity'] = data['messages']['avg_mccabe_complexity']
    data['stats']['repository_name'] = repo_name

    return data


# TODO plocka fram Max komplexitet / min komplexitet per commit
def _parse_pylint_messages(messages: list[Message], commit: str) -> dict[str, any]:
    """Parses Pylint Messages and returns them in a formatted dictionary using strings"""

    data = {}
    for msg in messages:
        module = msg.module
        if module not in data:
            data[module] = {'total_messages': 0, 'categories': {}}

        category = msg.category
        if category not in data[module]['categories']:
            data[module]['categories'][category] = {'total': 0, 'message_ids': {}}

        msg_id = msg.msg_id
        if msg_id not in data[module]['categories'][category]['message_ids']:
            data[module]['categories'][category]['message_ids'][msg_id] = []
        data[module]['categories'][category]['message_ids'][msg_id].append({
            'symbol': msg.symbol,
            'msg': msg.msg,
            'confidence': msg.confidence,
            'path': msg.path
        })

        data[module]['total_messages'] += 1
        data[module]['categories'][category]['total'] += 1

    data['avg_mccabe_complexity'] = _calculate_avg_mccabe_complexity(messages)

    logging.info(f"Result: {len(messages)} Pylint messages\n")

    return data


def _calculate_avg_mccabe_complexity(messages: list[Message]) -> float:
    """Calculates the average McCabe complexity of functions in a Python file."""

    total_complexity = 0
    complexity_count = 0
    for msg in messages:
        if msg.symbol == 'too-complex':
            complexity_value = [int(s) for s in msg.msg.split() if s.isdigit()]
            if complexity_value:
                total_complexity += complexity_value[0]
                complexity_count += 1

    average_complexity = total_complexity / complexity_count if complexity_count else 0

    return average_complexity
