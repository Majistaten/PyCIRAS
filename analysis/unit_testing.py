from git import Repo
from pathlib import Path
from utility import util
import ast
import logging
from utility.progress_bars import RichIterableProgressBar


# TODO Refine to more accurately detect testing as it looks in all different framework
# 1. Detects functions "test_" that are unittest, but stores in pytest-functions
# 2. Mer relevant att ta test-2-code ratio för ett helt repo per commit?
class TestFrameworkVisitor(ast.NodeVisitor):
    def __init__(self):
        self.known_test_modules = ['unittest', 'pytest', 'nose2']
        self.test_imports = []
        self.unittest_classes = []
        self.pytest_functions = []
        self.test_lines = 0
        # self.code_lines = 0
        self.file_line_count = 0  # TODO must be Total lines in the file being analyzed, excluding comments, whitespace and docstrings

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name in self.known_test_modules:
                self.test_imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in self.known_test_modules:
            self.test_imports.append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        if any(base.id == 'TestCase' for base in node.bases if isinstance(base, ast.Name)):
            self.unittest_classes.append(node.name)
            # Consider class definitions as part of test code
            self.test_lines += len(node.body)
        else:
            pass
            # Consider other classes as part of code
            # self.code_lines += len(node.body)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name.startswith('test_'):
            self.pytest_functions.append(node.name)
            # Consider test functions as part of test code
            self.test_lines += len(node.body)
        else:
            pass
            # Consider other functions as part of code
            # self.code_lines += len(node.body)
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

    total_code_lines = 0
    total_test_code_lines = 0
    visitor = TestFrameworkVisitor()
    for path in target_file_paths:

        visitor.test_imports = []
        visitor.unittest_classes = []
        visitor.pytest_functions = []
        visitor.test_lines = 0
        visitor.code_lines = 0
        try:
            with open(path, 'r', encoding='utf-8') as file:

                file_content = file.read()

                # TODO This is a simplified approach; need more sophisticated parsing
                file_line_count = sum(1 for line in file_content.split('\n') if line.strip() and not line.strip().startswith('#'))
                visitor.file_line_count = file_line_count

                tree = ast.parse(file_content)
                relative_path = util.get_file_relative_path_from_absolute_path(path)
                visitor.visit(tree)

                result['files'][relative_path] = {
                    'imports': visitor.test_imports,
                    'unittest_classes': visitor.unittest_classes,
                    'pytest_functions': visitor.pytest_functions
                }

                total_test_code_lines += visitor.test_lines
                total_code_lines += file_line_count - visitor.test_lines  # Assuming all non-test lines are code lines

        except SyntaxError as e:
            logging.error(f"Syntax error when executing AST analysis in file {relative_path}: {e}")
            continue

    # Calculate and add the repository-wide test-to-code ratio
    if total_code_lines > 0:  # Avoid division by zero
        result['test-to-code-ratio'] = total_test_code_lines / total_code_lines
    else:
        result['test-to-code-ratio'] = float('inf') if total_test_code_lines > 0 else 0

    return result

