from pathlib import Path

from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.reporters.ureports.nodes import Section
from pylint.message import Message
from io import StringIO
import logging
from git import Repo
from utility import util, config
from utility.progress_bars import RichIterableProgressBar
from rich.pretty import pprint


class LintReporter(TextReporter):
    """Custom Pylint reporter, collects linting messages and allows for further processing"""

    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages: list[Message] = []

    def _display(self, layout: Section):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def mine_lint_data(repo_paths_with_commits: dict[str, any]) -> dict[str, any]:
    """Get Pylint metrics from the commits of multiple git repositories"""
    metrics = {}
    for repo_path, commits in repo_paths_with_commits.items():
        logging.info(f"Code quality: inspecting {repo_path}")
        metrics[util.get_repo_name_from_path(repo_path)] = _extract_pylint_metrics(Path(repo_path), commits)

    return metrics


def _extract_pylint_metrics(repository_path: Path, commits: any) -> dict[str, any]:
    """Extract Pylint metrics from a the commits of a single repository"""
    metrics = {}
    repo = Repo(repository_path)
    for commit in RichIterableProgressBar(commits,
                                          description=f"Traversing commits, extracting lint data",
                                          postfix=util.get_repo_name_from_path(str(repository_path)),
                                          disable=config.DISABLE_PROGRESS_BARS):
        commit_hash = commit["commit_hash"]

        date = commit["date"]
        repo.git.checkout(commit_hash)
        lint_data = _run_pylint(repository_path, commit_hash)

        if lint_data is not None:
            metrics[commit_hash] = lint_data
            metrics[commit_hash]['date'] = date

    return metrics


def _run_pylint(repository_path: Path, commit: str) -> dict[str, any] | None:
    """Execute Pylint on a single repository, get the report in a dict"""
    result = {}
    target_files = util.get_python_files_from_directory(repository_path)
    if target_files is None or len(target_files) == 0:
        logging.warning(f"\nNo python files found in "
                        f"{util.get_file_relative_path_from_absolute_path(str(repository_path))}"
                        f" when executing lint mining.\n"
                        f"Skipping commit: {commit}")
        return None
    elif len(target_files) > 1000:
        logging.warning(
            f"Found {len(target_files)} files in {repository_path}. "
            f"This might take a while, consider skipping this repository.")

    out = StringIO()
    reporter = LintReporter(output=out)

    logging.info(f"Analyzing {len(target_files)} files in {repository_path}")

    run = Run([f'--rcfile={config.PYLINT_CONFIG}'] + target_files, reporter=reporter, exit=False)
    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {str(attr): getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    repository_name = util.get_repo_name_from_path(str(repository_path))
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
            result[module]['categories'][category]['message_ids'][msg_id] = []
        result[module]['categories'][category]['message_ids'][msg_id].append({
            'symbol': msg.symbol,
            'msg': msg.msg,
            'confidence': msg.confidence,
            'path': msg.path
        })

        result[module]['total_messages'] += 1
        result[module]['categories'][category]['total'] += 1

    result['avg_mccabe_complexity'] = get_average_complexity(messages)
    logging.info(f"Extracted {len(result)} modules")
    return result


def get_average_complexity(messages: list[Message]) -> float:
    """Calculates the average McCabe Rating for 'too-complex' messages from the given list of Pylint messages."""
    total_complexity = 0
    complexity_count = 0

    for msg in messages:
        if msg.symbol == 'too-complex':
            complexity_value = [int(s) for s in msg.msg.split() if s.isdigit()]
            pprint(complexity_value)
            if complexity_value:
                total_complexity += complexity_value[0]
                complexity_count += 1

    average_complexity = total_complexity / complexity_count if complexity_count else 0
    return average_complexity

