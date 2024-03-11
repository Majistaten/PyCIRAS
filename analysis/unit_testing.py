import pprint
from analysis import git_miner
from pathlib import Path
from utility import config, util
import ast
import logging


# TODO Verify that it works reliably for all mentioned frameworks

# TODO
# Skapa en dictionary
# {
#   'repository-xyz': {
#       commits: {
#          'fh7a872j0087he': { # commit hash
#              'thing.py': { # filnamn
#                  'imports': [
#                      'import unittest', # importrader
#                      'import pytest',
#                      '...'
#                  ],
#                   'classes': [
#                      'TestThing', # klassrader
#                      'TestThing2',
#                      '...'
#                  ],
#                   'functions': [
#                      'test_thing', # funktionsrader
#                      'test_thing2',
#                      '...'
#                  ]
#              },
#              'thing2.py': {}
#          },
#         'fh7a872j0087he2': {}
#       },
#       test-to-code-ratio: 0.5
#   },
#   'repository-abc': {}
# }

# För varje repo, loopa igenom alla commits, för varje commit, loopa igenom alla filer,
# kör analyze_file_for_tests och spara resultaten i dictionaryn, returnera den
def mine_unit_testing_metrics(repo_urls: list[str]) -> dict[str, [dict]]:

    metrics = {}

    repo_urls_with_hashes_and_dates = git_miner.get_repo_urls_with_commit_hashes_and_dates(repo_urls, repository_directory=config.REPOSITORIES_FOLDER)
    for repo_url, commits in repo_urls_with_hashes_and_dates.items():
        logging.info(f"Unit Testing: inspecting {repo_url}")



        pass
           #  find eve...

    pprint.pprint(repo_urls_with_hashes_and_dates)

    print("Mining unit testing metrics for repo: ", repo_urls)


#TODO rename
def find_evidence_of_unit_testing(repository_directory: Path):
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



# Vad den gör just nu
# Itererar över alla filer i ett repo dir
# För varje fil:
# visitar filen med en visitor
# visitorn samlar alla imports i lista,
# Visitorn kollar klassdefinitioner och sparar klassnamn om det är en unittest.TestCase
# Visitorn kollar funktioner och sparar funktionnamn om det börjar med test_

# TODO visitorklassen
# Lagra bara imports som är från unittest, pytest, nose2 - se till att det är heltäckande
# Kolla klassdefinitioner om det är en unittest.TestCase, nose 2 eller pytest equivalent
# Kolla funktiondefinitioner om det är någon form av testmetod som börjar med test_ - se till att det är heltäckande för alla frameworks
#
# Test 2 code ratio?
class TestFrameworkVisitor(ast.NodeVisitor):
    def __init__(self):

        self.imports = []

        self.unittest_classes = []

        self.pytest_functions = []

    # TODO skillnad på import och importfrom?
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


# TODO
# Eventuellt nollställa visitorn istället för att instansiera en ny för varje fil
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





if __name__ == '__main__':
    """Example usage of the find_evidence_of_unit_testing function."""
    # repository_directory = "../repositories/amalfi-artifact"
    repository_directory = config.REPOSITORIES_FOLDER / 'TDD-Hangman'
    evidence = find_evidence_of_unit_testing(repository_directory)

    print(f"Found evidence of unit testing:")

    pprint.pprint(evidence)
