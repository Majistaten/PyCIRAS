from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.message import Message
from io import StringIO
import os
import pprint


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
                'symbol': msg.symbol,
                'message': msg.msg,
                'occurrences': []
            }

        result[module]['total_messages'] += 1
        result[module]['categories'][category]['total'] += 1
        result[module]['categories'][category]['message_ids'][msg_id]['count'] += 1
        result[module]['categories'][category]['message_ids'][msg_id]['occurrences'].append({
            'line': msg.line,
            'column': msg.column,
        })

    return result


def get_python_files_from_directory(directory):
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                print(f"Found: {str(os.path.join(root, file))}")
                python_files.append(str(os.path.join(root, file)))
    return python_files


def analyze_repository(repository_path):
    result = {}
    target_files = get_python_files_from_directory(repository_path)
    out = StringIO()
    reporter = LintReporter(output=out)
    run = Run(target_files, reporter=reporter, exit=False)
    stats = run.linter.stats
    if not isinstance(stats, dict):
        stats_dict = {attr: getattr(stats, attr) for attr in dir(stats) if
                      not attr.startswith('__') and not callable(getattr(stats, attr))}
    else:
        stats_dict = stats

    result['messages'] = lint_message_extraction(reporter.messages)
    result['stats'] = stats_dict

    return result


if __name__ == '__main__':
    classification = analyze_repository("../repositories/NDStudy")

    print("\nClassification Results:")
    for module, info in classification["messages"].items():
        print(f"Module: {module}, Total Messages: {info['total_messages']}")
        for category, cat_info in info['categories'].items():
            print(" " * 2 + f"Category: {category}, Total: {cat_info['total']}")
            for msg_id, msg_info in cat_info['message_ids'].items():
                print(" " * 4 + f"Message ID: {msg_id}, Count: {msg_info['count']}")
                print(" " * 6 + f"Symbol: {msg_info['symbol']}")

    pprint.pprint(classification["stats"])