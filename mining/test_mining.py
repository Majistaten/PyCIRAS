from git import Repo
from pathlib import Path
from utility import util, config
import ast
import logging
from utility.progress_bars import RichIterableProgressBar
from rich.pretty import pprint


class StatementVisitor(ast.NodeVisitor):
    def __init__(self):
        self.known_test_modules = ['unittest', 'pytest', 'nose2']
        self.test_imports = []
        self.test_classes = []
        self.test_functions = []
        self.test_statements = 0
        self.production_statements = 0
        self.in_test_context = False

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in self.known_test_modules:
                self.test_statements += 1
                self.test_imports.append(alias.name)

            elif not self.in_test_context:
                self.production_statements += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        original_in_test_context = self.in_test_context

        test_base_found = False
        for base in node.bases:
            # Check if the base is directly an ast.Name and matches 'TestCase'
            if isinstance(base, ast.Name) and base.id == "TestCase":
                test_base_found = True
                break
            # Additionally, check if the base is an ast.Attribute
            elif isinstance(base, ast.Attribute) and base.attr == "TestCase":
                test_base_found = True
                break

        if test_base_found:
            self.test_statements += 1
            self.test_classes.append(node.name)
            self.in_test_context = True
        else:
            if not self.in_test_context:
                self.production_statements += 1

        self.generic_visit(node)
        self.in_test_context = original_in_test_context

    def visit_FunctionDef(self, node):
        original_in_test_context = self.in_test_context
        if node.name.startswith('test_'):
            self.test_functions.append(node.name)
            self.test_statements += 1
            self.in_test_context = True
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


def mine_test_data(repo_paths_with_commits: dict[str, any]) -> dict[str, any]:
    """Get unit-testing metrics from the commits of multiple git repositories"""
    metrics = {}
    for repo_path, commits in repo_paths_with_commits.items():
        logging.info(f"Unit Testing: inspecting {repo_path}")
        metrics[util.get_repo_name_from_path(repo_path)] = _extract_unit_testing_metrics(Path(repo_path), commits)

    return metrics


def _extract_unit_testing_metrics(repository_path: Path, commits: any) -> dict[str, any]:
    """Extract unit-testing metrics from a the commits of a single repository"""
    metrics = {}
    repo = Repo(repository_path)
    for commit in RichIterableProgressBar(commits,
                                          description=f"Traversing commits, extracting unit-testing metrics",
                                          postfix=util.get_repo_name_from_path(str(repository_path)),
                                          disable=config.DISABLE_PROGRESS_BARS):
        commit_hash = commit["commit_hash"]

        date = commit["date"]
        repo.git.checkout(commit_hash)
        test_data = _run_ast_analysis(repository_path, commit_hash)

        if test_data is not None:
            metrics[commit_hash] = test_data
            metrics[commit_hash]['date'] = date

    return metrics


def _run_ast_analysis(repository_path: Path, commit: str) -> dict[str, any] | None:
    """Run the AST mining on the files in the repository"""
    target_file_paths = util.get_python_files_from_directory(repository_path)
    if target_file_paths is None or len(target_file_paths) == 0:
        logging.warning(f"\nNo python files found in "
                        f"{util.get_file_relative_path_from_absolute_path(str(repository_path))}"
                        f" when executing test mining.\n"
                        f"Skipping commit: {commit}")
        return None

    result = {
        'files': {},
        'test-to-code-ratio': 0.0
    }

    total_production_statements = 0
    total_test_statements = 0
    visitor = StatementVisitor()
    for path in target_file_paths:
        visitor.test_imports = []
        visitor.test_classes = []
        visitor.test_functions = []
        visitor.test_statements = 0
        visitor.production_statements = 0
        try:
            with open(path, 'r', encoding='utf-8') as file:
                relative_path = util.get_file_relative_path_from_absolute_path(path)
                tree = ast.parse(file.read())
                visitor.visit(tree)

                result['files'][relative_path] = {
                    'imports': visitor.test_imports,
                    'unittest_classes': visitor.test_classes,
                    'pytest_functions': visitor.test_functions,
                    'production_statements': visitor.production_statements,
                    'test_statements': visitor.test_statements
                }

                total_test_statements += visitor.test_statements
                total_production_statements += visitor.production_statements

        except SyntaxError as e:
            logging.error(f"Syntax error when executing AST mining in file "
                          f"{relative_path}: {e} \nSkipping this file.")
            continue

    # Calculate and add the repository-wide test-to-code ratio
    total_statements = total_test_statements + total_production_statements
    if total_statements > 0:  # Avoid division by zero
        result['test-to-code-ratio'] = total_test_statements / total_statements
    else:
        result['test-to-code-ratio'] = 1.0 if total_test_statements > 0 else 0

    return result
