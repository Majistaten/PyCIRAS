from pylint.lint import Run
from pylint.reporters.text import TextReporter
from pylint.message import Message
from io import StringIO


class LintReporter(TextReporter):
    def __init__(self, output=None):
        super().__init__(output=output)
        self.messages = []

    def _display(self, layout):
        pass

    def handle_message(self, msg: Message):
        self.messages.append(msg)


def classify_lint_messages(messages):
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


if __name__ == '__main__':
    target_files = ["../pylint-test.py", "../pylint-test2.py"]
    out = StringIO()
    reporter = LintReporter(output=out)
    Run(target_files, reporter=reporter, exit=False)
    print("-" * 20)
    print(reporter.messages)
    print("-" * 20)
    classification = classify_lint_messages(reporter.messages)

    print("\nClassification Results:")
    for module, info in classification.items():
        print(f"Module: {module}, Total Messages: {info['total_messages']}")
        for category, cat_info in info['categories'].items():
            print(" " * 2 + f"Category: {category}, Total: {cat_info['total']}")
            for msg_id, msg_info in cat_info['message_ids'].items():
                print(" " * 4 + f"Message ID: {msg_id}, Count: {msg_info['count']}")
                print(" " * 6 + f"Message: {msg_info['message']}")
                for occurrence in msg_info['occurrences']:
                    print(" " * 8 + f"Occurrence: Line {occurrence['line']}, Column {occurrence['column']}")
