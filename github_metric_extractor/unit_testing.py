import util
import re
import ast


# TODO Verify that it works reliably for all mentioned frameworks

# TODO Add functionality for traversing commits and create a structured results dictionary

class TestFrameworkVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.unittest_classes = []
        self.pytest_functions = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        if any(base.id == 'TestCase' for base in node.bases if isinstance(base, ast.Name)):
            self.unittest_classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            self.pytest_functions.append(node.name)
        self.generic_visit(node)


def analyze_file_for_tests(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            tree = ast.parse(content)
            visitor = TestFrameworkVisitor()
            visitor.visit(tree)
            return visitor
    except SyntaxError as e:
        print(f"Syntax error in file {file_path}: {e}")
        return TestFrameworkVisitor()  # Return an empty visitor if you want to keep processing other file


def find_evidence_of_unit_testing(repository_directory: str):
    evidence = {
        'unittest': [],
        'pytest': [],
        'nose2': [],  # Add a section for nose2
        'general_imports': []
    }
    for file_path in util.get_python_files_from_directory(repository_directory):
        analysis = analyze_file_for_tests(file_path)
        if 'unittest' in analysis.imports:
            evidence['unittest'].append(file_path)
        if 'pytest' in analysis.imports:
            evidence['pytest'].append(file_path)
        if 'nose2' in analysis.imports:
            evidence['nose2'].append(file_path)
        if analysis.unittest_classes or analysis.pytest_functions:
            evidence['general_imports'].append(file_path)
    return evidence


if __name__ == '__main__':
    # repository_directory = "../repositories/amalfi-artifact"
    repository_directory = "../repositories/smartbugs"
    evidence = find_evidence_of_unit_testing(repository_directory)
    print(f"Found evidence of unit testing: {evidence}")
