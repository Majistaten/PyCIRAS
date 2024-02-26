from pylint.checkers import BaseChecker
from pylint.lint import Run
from pylint.reporters.text import TextReporter
from io import StringIO


class SomeReporter(TextReporter):
    def __init__(self, output=None):
        super().__init__(output)
        self.content = []

    def write(self, string):
        self.content.append(string)

    def read(self):
        return self.content


def classify_lint_messages(messages):
    classification = {'error': [], 'warning': [], 'refactor': [], 'convention': [], 'fatal': []}
    for msg in messages:
        if msg.category in classification:
            classification[msg.category].append(msg)
    return classification


if __name__ == '__main__':
    target_files = ["../pylint-test.py", "../pylint-test2.py"]
    out = StringIO()
    reporter = SomeReporter(out)
    Run(target_files, reporter=reporter, exit=False)
    classification = classify_lint_messages(reporter.messages)
    print(classification)
    print("NIFTY LITTLE LINE TO SHARE WITH YOUR BUDDIES")
    for line in out.read():
        print(line)
    print("NIFTY LITTLE LINE TO SHARE WITH YOUR BUDDIES")
    for k, v in classification.items():
        print(f"{k}: {[vi + ' Ass ' for vi in v]}")
