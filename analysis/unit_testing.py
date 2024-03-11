import pprint

from git import Repo

from analysis import git_miner
from pathlib import Path
from utility import config, util
import ast
import logging
from utility.progress_bars import RichIterableProgressBar

# TODO
# Skapa en dictionary
# {
#   'repository-xyz': {
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
#              'test-to-code-ratio': 0.5
#          },
#         'fh7a872j0087he2': {}
#       },
#   },
#   'repository-abc': {}
# }

# Vad den gör just nu
# Itererar över alla filer i ett repo dir
# För varje fil:
# visitar filen med en visitor
# visitorn samlar alla imports i lista,
# Visitorn kollar klassdefinitioner och sparar klassnamn om det är en unittest.TestCase
# Visitorn kollar funktioner och sparar funktionnamn om det börjar med test_
# TODO
# Lagra bara imports som är från unittest, pytest, nose2 - se till att det är heltäckande
# Kolla klassdefinitioner om det är en unittest.TestCase, nose 2 eller pytest equivalent
# Kolla funktiondefinitioner om det är någon form av testmetod som börjar med test_ - se till att det är heltäckande för alla frameworks
# TODO Verify that it works reliably for all mentioned frameworks
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


def mine_unit_testing_metrics(repo_paths_with_commits: dict[str, any]) -> dict[str, any]:
    """Get unit-testing metrics from the commits of multiple git repositories"""
    metrics = {}
    for repo_path, commits in repo_paths_with_commits.items():
        logging.info(f"Unit Testing: inspecting {repo_path}")
        metrics[util.get_repo_name_from_url(repo_path)] = _extract_unit_testing_metrics(Path(repo_path), commits)

    return metrics


def _extract_unit_testing_metrics(repository_path: Path, commits: any) -> dict[str, any]:
    """Extract unit-testing metrics from a the commits of a single repository"""
    metrics = {}
    repo = Repo(repository_path)
    for commit in RichIterableProgressBar(commits,
                                          description=f"Traversing commits, extracting unit-testing metrics",
                                          postfix=util.get_repo_name_from_path(str(repository_path))):
        commit_hash = commit["commit_hash"]
        date = commit["date"]
        repo.git.checkout(commit_hash)
        metrics[commit_hash] = _run_ast_analysis(repository_path)
        if metrics[commit_hash] is not None:
            metrics[commit_hash]['date'] = date

    return metrics


# TODO
# Kolla upp om test-to code är en gångbar metric akademiskt, om inte, alternativ?
def _run_ast_analysis(repository_path: Path) -> dict[str, any] | None:
    """Run the AST analysis on the files in the repository"""
    target_file_paths = util.get_python_files_from_directory(repository_path)
    if target_file_paths is None or len(target_file_paths) == 0:
        logging.info(f"No python files found in {repository_path}")
        return None

    result = {}
    visitor = TestFrameworkVisitor()
    for path in target_file_paths:

        visitor.imports = []
        visitor.unittest_classes = []
        visitor.pytest_functions = []

        try:
            with open(path, 'r', encoding='utf-8') as file:
                tree = ast.parse(file.read())
                relative_path = util.get_file_reqlative_path_from_absolute_path(path)
                visitor.visit(tree)

                result[relative_path] = {}
                result[relative_path]['imports'] = visitor.imports
                result[relative_path]['classes'] = visitor.unittest_classes
                result[relative_path]['functions'] = visitor.pytest_functions

        except SyntaxError as e:
            logging.error(f"Syntax error when executing AST analysis in file {relative_path}: {e}")
            continue

    return result

