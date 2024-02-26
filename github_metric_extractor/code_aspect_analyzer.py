from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.message import Message
from io import StringIO
import os
import pprint
import logging
from tqdm import tqdm


class LintReporter(TextReporter):
    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages = []

    def _display(self, layout):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def lint_message_extraction(messages):
    result = {}
    logging.info(f"Extracting messages from {len(messages)} messages")
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


def get_python_files_from_directory(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                logging.info(f"Found python file: {str(os.path.join(root, file))}")
                python_files.append(str(os.path.join(root, file)))
    return python_files


def analyze_repository(repository_path):
    result = {}
    target_files = get_python_files_from_directory(repository_path)
    if target_files is None or len(target_files) == 0:
        logging.warning(f"No python files found in {repository_path}")
        return result
    out = StringIO()
    reporter = LintReporter(output=out)
    logging.info(f"Analyzing {len(target_files)} files in {repository_path}")
    run = Run(target_files, reporter=reporter, exit=False)
    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {attr: getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    result['messages'] = lint_message_extraction(reporter.messages)
    result['stats'] = stats_dict
    logging.info(f"Analyzed {len(target_files)} files in {repository_path}")
    return result


def analyze_repositories(repositories):
    results = {}
    for repository in tqdm(repositories, desc="Analyzing repositories"):
        logging.info(f"Analyzing repository {repository}")
        results[repository] = analyze_repository(repository)
    return results


if __name__ == '__main__':
    # result = analyze_repository("../analyze_files")
    logging.basicConfig(level=logging.WARN, format='%(asctime)s - %(levelname)s - %(message)s')
    repositories = [
        os.path.join("../repositories", repo) for repo in os.listdir("../repositories")
        if os.path.isdir(os.path.join("../repositories", repo))
    ]

    # result = analyze_repository("../repositories/astnn")
    result = analyze_repositories(repositories)
    pprint.pprint(result, width=300, indent=3)
