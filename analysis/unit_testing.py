from git import Repo
from pathlib import Path
from utility import util
import ast
import logging
from utility.progress_bars import RichIterableProgressBar


# TODO function defenitions are common for unittest and pytest, not specifically pytest
class StatementVisitor(ast.NodeVisitor):
    def __init__(self):
        self.known_test_modules = ['unittest', 'pytest', 'nose2']
        self.test_statements = 0
        self.production_statements = 0
        self.in_test_context = False

    def visit_Import(self, node):
        if any(alias.name in self.known_test_modules for alias in node.names):
            self.test_statements += 1
        elif not self.in_test_context:
            self.production_statements += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        original_in_test_context = self.in_test_context
        if "TestCase" in [base.id for base in node.bases if isinstance(base, ast.Name)]:
            self.in_test_context = True
            self.test_statements += 1
        else:
            if not self.in_test_context:
                self.production_statements += 1
        self.generic_visit(node)
        self.in_test_context = original_in_test_context

    def visit_FunctionDef(self, node):
        original_in_test_context = self.in_test_context
        if node.name.startswith('test_'):
            self.in_test_context = True
            self.test_statements += 1
        else:
            if not self.in_test_context:
                self.production_statements += 1
        self.generic_visit(node)
        self.in_test_context = original_in_test_context

    def visit_Assign(self, node):
        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1
        self.generic_visit(node)

    def visit_Expr(self, node):
        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1
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


def _run_ast_analysis(repository_path: Path) -> dict[str, any] | None:
    """Run the AST analysis on the files in the repository"""
    target_file_paths = util.get_python_files_from_directory(repository_path)
    if target_file_paths is None or len(target_file_paths) == 0:
        logging.info(f"No python files found in {repository_path}")
        return None

    result = {
        'files': {},
        'test-to-code-ratio': 0
    }

    total_production_statements = 0
    total_test_statements = 0
    visitor = StatementVisitor()
    for path in target_file_paths:
        visitor.test_imports = []
        visitor.unittest_classes = []
        visitor.pytest_functions = []
        visitor.test_statements = 0
        visitor.production_statements = 0
        try:
            with open(path, 'r', encoding='utf-8') as file:
                tree = ast.parse(file.read())
                relative_path = util.get_file_relative_path_from_absolute_path(path)
                visitor.visit(tree)

                result['files'][relative_path] = {
                    'imports': visitor.test_imports,
                    'unittest_classes': visitor.unittest_classes,
                    'pytest_functions': visitor.pytest_functions,
                    'production_statements': visitor.production_statements,
                    'test_statements': visitor.test_statements
                }

                total_test_statements += visitor.test_statements
                total_production_statements += visitor.production_statements

        # TODO wierd progressbar/error when this happens
        except SyntaxError as e:
            logging.error(f"Syntax error when executing AST analysis in file {relative_path}: {e}")
            continue

    # Calculate and add the repository-wide test-to-code ratio
    total_statements = total_test_statements + total_production_statements
    if total_statements > 0:  # Avoid division by zero
        result['test-to-code-ratio'] = total_test_statements / total_statements
    else:
        result['test-to-code-ratio'] = 1.0 if total_test_statements > 0 else 0

    return result
