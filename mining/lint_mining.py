import logging
from datetime import datetime
from io import StringIO
from pathlib import Path

from git import Repo
from pylint.lint import Run
from pylint.message import Message, MessageIdStore
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
        data[util.get_repo_name_from_url_or_path(repo_path)] = _mine_commit_data(Path(repo_path),
                                                                                 commit_metadata,
                                                                                 progress)

    return data


def _mine_commit_data(repo_path: Path,
                      commit_metadata: [tuple[str, datetime]],
                      progress: Progress) -> dict[str, any]:
    """Mines lint data from the commits of a repository"""

    data = {}
    repo = Repo(repo_path)
    for commit_hash, date in IterableProgressWrapper(commit_metadata,
                                                     progress,
                                                     description=util.get_repo_name_from_url_or_path(repo_path),
                                                     postfix='Commits'):

        # Ensure the repo is in a clean state
        repo.git.reset('--hard')
        repo.git.clean('-fdx')

        repo.git.checkout(commit_hash)
        lint_data = _run_pylint(repo_path, commit_hash)

        if lint_data is not None:
            data[commit_hash] = lint_data
            data[commit_hash]['date'] = date

    return data


def _run_pylint(repository_path: Path, commit: str) -> dict[str, any] | None:
    """Runs Pylint on Python files"""

    data = {}

    out = StringIO()
    reporter = LintReporter(output=out)

    escaped_chars = [f'\\{char}' if char in {'.', '^', '$', '*', '+', '?', '{', '}', '[', ']', '\\', '|', '(', ')'}
                     else char for char in config.IGNORE_STARTSWITH]

    re_ignore = r'.*[/\\]' + r'[' + r'|'.join(escaped_chars) + r']' + r'.*[/\\].*$'

    pylint_options = [
        str(repository_path),
        f'--rcfile={config.PYLINT_CONFIG}',
        f'--ignore={",".join(util.generate_dir_name_variations(config.IGNORE_DIRECTORIES))}',
        f"--ignore-paths={re_ignore}",
    ]

    run = Run(pylint_options, reporter=reporter, exit=False)

    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {str(attr): getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    repo_name = util.get_repo_name_from_url_or_path(str(repository_path))

    data['messages'] = _parse_pylint_messages(reporter.messages, commit)
    data['messages']['repository_name'] = repo_name

    stats_dict = _append_message_ids(stats_dict, run.linter.msgs_store.message_id_store)

    data['stats'] = stats_dict
    data['stats']['avg_mccabe_complexity'] = data['messages']['avg_mccabe_complexity']
    data['stats']['repository_name'] = repo_name

    return data


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

    logging.info(f"{commit}: {len(messages)} Pylint messages\n")

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


def _append_message_ids(stats_dict: dict, message_id_store: MessageIdStore) -> dict[str, any]:
    """Appends message IDs to the pylint messages"""

    if 'by_msg' in stats_dict:
        new_by_msg = {}
        for symbol, count in stats_dict['by_msg'].items():
            try:
                msgid = message_id_store.get_msgid(symbol)
                new_key = f"{msgid}.{symbol}"
                new_by_msg[new_key] = count
            except Exception as e:
                logging.error(f"Could not find message ID for symbol '{symbol}': {e}")
        stats_dict['by_msg'] = new_by_msg

    return stats_dict
