from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.reporters.ureports.nodes import Section
from pylint.message import Message
from io import StringIO
import os
import pprint
import logging
from tqdm import tqdm
from git import Repo, Git
import util


class LintReporter(TextReporter):
    """Custom Pylint reporter, collects linting messages and allows for further processing"""

    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages: list[Message] = []

    def _display(self, layout: Section):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def analyze_repositories_commits(repo_commits: dict[str, any]) -> dict[str, any]:
    """Analyze commits for multiple repositories"""
    results = {}
    for repository, commits in repo_commits.items():
        logging.info(f"Analyzing repository {repository}")
        results[repository] = analyze_repository_commits(repository, commits)
    return results


def analyze_repository_commits(repository_path: str, commits: any) -> dict[str, any]:
    """Analyze commits for a single repository"""
    results = {}
    repo = Repo(repository_path)
    for commit in tqdm(commits, desc=f"Analyzing commits", postfix=repository_path, ncols=100, colour="blue"):
        hash = commit["commit_hash"]
        repo.git.checkout(hash)
        results[hash] = analyze_repository(repository_path)
    return results


def analyze_repository(repository_path: str) -> dict[str, any] | None:
    """Analyze a single repository"""
    result = {}
    target_files = util.get_python_files_from_directory(repository_path)
    if target_files is None or len(target_files) == 0:
        logging.warning(f"No python files found in {repository_path}")
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

    result['messages'] = lint_message_extraction(reporter.messages)
    result['stats'] = stats_dict

    logging.info(f"Analyzed {len(target_files)} files in {repository_path}")

    return result


def lint_message_extraction(messages: list[Message]) -> dict[str, any]:
    """Extracts Pylint messages and returns them in a formatted dictionary"""

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


def analyze_repositories(repositories):
    """Analyze multiple repositories"""
    results = {}
    for repository in tqdm(repositories, desc="Analyzing repositories", ncols=100, colour="blue"):
        logging.info(f"Analyzing repository {repository}")
        results[repository] = analyze_repository(repository)
    return results


if __name__ == '__main__':
    """"Test script for analyzing repositories"""

    # result = analyze_repository("../analyze_files")
    logging.basicConfig(level=logging.WARN, format='%(asctime)s - %(levelname)s - %(message)s')
    repositories = [
        os.path.join("../repositories", repo) for repo in os.listdir("../repositories")
        if os.path.isdir(os.path.join("../repositories", repo))
    ]

    # result = analyze_repository("../repositories/astnn")
    result = analyze_repositories(repositories)
    pprint.pprint(result, width=300, indent=3)
