import ast
import logging
from datetime import datetime
from pathlib import Path

from git import Repo
from rich.progress import (
    Progress
)

from utility import config, util
from utility.progress_bars import IterableProgressWrapper


# TODO add exclusions for datasets/venv etc

class StatementVisitor(ast.NodeVisitor):
    """Used to find unit-testing imports and count test/production statements in a Python file"""

    def __init__(self):
        self.known_test_modules = ['unittest', 'pytest', 'nose2']
        self.test_imports = []
        self.test_classes = []
        self.test_functions = []
        self.test_statements = 0
        self.production_statements = 0
        self.in_test_context = False

    def visit_Import(self, node):
        """Parse an import"""

        for alias in node.names:
            if alias.name in self.known_test_modules:
                self.test_statements += 1
                self.test_imports.append(alias.name)

            elif not self.in_test_context:
                self.production_statements += 1

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Parse a class definition, set the context for coming visits"""

        original_in_test_context = self.in_test_context
        test_base_found = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "TestCase":
                test_base_found = True
                break

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
        """Parse a function definition"""

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
        """Parse an assignment"""

        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1

        self.generic_visit(node)

    def visit_Call(self, node):
        """Parse a function call"""

        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1

        self.generic_visit(node)

    def visit_Expr(self, node):
        """Parse an expression"""

        if self.in_test_context:
            self.test_statements += 1
        else:
            self.production_statements += 1

        self.generic_visit(node)


def mine_test_data(repo_paths_with_commit_metadata: dict[str, list[tuple[str, datetime]]],
                   progress: Progress) -> dict[str, any]:
    """Mine unit-testing data from the commits of multiple git repositories"""

    data = {}
    for repo_path, commit_metadata in IterableProgressWrapper(repo_paths_with_commit_metadata.items(),
                                                              progress,
                                                              description="Mining test data",
                                                              postfix="Repos"):
        logging.info(f"\nMining test data: {repo_path}")
        data[util.get_repo_name_from_url_or_path(repo_path)] = _mine_commit_data(Path(repo_path),
                                                                                 commit_metadata,
                                                                                 progress)

    return data


def _mine_commit_data(repo_path: Path,
                      commit_metadata: [tuple[str, datetime]],
                      progress: Progress) -> dict[str, any]:
    """Mines test data from the commits of a repository"""

    data = {}
    repo = Repo(repo_path)
    for commit_hash, date in IterableProgressWrapper(commit_metadata,
                                                     progress,
                                                     description=util.get_repo_name_from_url_or_path(repo_path),
                                                     postfix='Commits'):

        # Ensure the repo is in a clean state
        repo.git.reset('--hard')
        repo.git.clean('-fdx')

        repo.git.checkout(commit_hash)
        test_data = _run_ast_mining(repo_path, commit_hash, progress)

        if test_data is not None:
            data[commit_hash] = test_data
            data[commit_hash]['date'] = date

    return data


def _run_ast_mining(repo_path: Path,
                    commit: str,
                    progress: Progress) -> dict[str, any] | None:
    """Runs AST mining on Python files"""

    target_files = util.get_python_files_from_directory(repo_path,
                                                        config.IGNORE_DIRECTORIES,
                                                        config.IGNORE_STARTSWITH)
    if target_files is None or len(target_files) == 0:
        logging.warning(f"\nThis commit has no Python files\n"
                     f"Skipping commit: {commit}")
        return None

    data = {
        'files': {},
        'test-to-code-ratio': 0.0
    }

    logging.info(f'\n[{util.get_repo_name_from_url_or_path(repo_path)}]: {commit}\n'
                 f'Mining {len(target_files)} Python files')

    total_production_statements = 0
    total_test_statements = 0
    visitor = StatementVisitor()
    for path in IterableProgressWrapper(target_files,
                                        progress,
                                        description=commit,
                                        postfix='Python Files'):

        visitor.test_imports = []
        visitor.test_classes = []
        visitor.test_functions = []
        visitor.test_statements = 0
        visitor.production_statements = 0

        try:
            with open(path, 'r', encoding='utf-8') as file:

                relative_path = util.absolute_repos_to_relative(path)
                tree = ast.parse(file.read())
                visitor.visit(tree)

                data['files'][relative_path] = {
                    'imports': visitor.test_imports,
                    'unittest_classes': visitor.test_classes,
                    'pytest_functions': visitor.test_functions,
                    'production_statements': visitor.production_statements,
                    'test_statements': visitor.test_statements
                }

                total_test_statements += visitor.test_statements
                total_production_statements += visitor.production_statements

        except SyntaxError as e:
            logging.warning(f"\nTest Mining Syntax Error: "
                            f"{relative_path}: \n[{e}]\n\nSkipping this file.\n")

            continue

    data['test-to-code-ratio'] = _calculate_test_to_code_ratio(total_test_statements,
                                                               total_production_statements)

    return data


def _calculate_test_to_code_ratio(test_statements: float, production_statements: float) -> float:
    """Calculate the test-to-code ratio of a repository"""

    total_statements = test_statements + production_statements
    if total_statements > 0:
        return test_statements / total_statements
    else:
        return 1.0 if test_statements > 0 else 0
