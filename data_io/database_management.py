import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_io.data_management import CustomEncoder
from data_io.database_models import Base, Git, Lint, LintCommit, Metadata, Repository, Stargazers, Test, TestCommit


def dumps(data):
    return json.dumps(data, cls=CustomEncoder)

# TODO progress

class DatabaseManager:
    def __init__(self, database_path: Path):
        self.engine = create_engine(f'sqlite:///{database_path}', echo=False, json_serializer=dumps)
        Base.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine)

    def __enter__(self):
        self.session = self.session_maker()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def insert_metadata(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            metadata_entry = Metadata(repository_name=repo_name, data=repo_info)
            self.session.add(metadata_entry)

        self.session.commit()

    def insert_stargazers(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            stargazers_entry = Stargazers(repository_name=repo_name, data=repo_info)
            self.session.add(stargazers_entry)

        self.session.commit()

    def insert_tests(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            test_entry = Test(repository_name=repo_name)

            self.session.add(test_entry)
            self.session.commit()

            for commit, commit_info in repo_info.items():
                self.insert_test_commit(repo_name, commit, commit_info)

    def insert_test_commit(self, repo_name: str, commit: str, commit_info: dict):
        test = self.session.query(Test).filter_by(repository_name=repo_name).first()

        test_commit = TestCommit(hash=commit,
                                 files=commit_info['files'],
                                 test_to_code_ratio=commit_info['test-to-code-ratio'],
                                 date=commit_info['date'])
        test_commit.test = test

        self.session.add(test_commit)
        self.session.commit()

    def insert_lints(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            lint_entry = Lint(repository_name=repo_name)
            self.session.add(lint_entry)
            self.session.commit()

            for commit, commit_info in repo_info.items():
                self.insert_lint_commit(repo_name, commit, commit_info)

    def insert_lint_commit(self, repo_name: str, commit: str, commit_info: dict):
        lint = self.session.query(Lint).filter_by(repository_name=repo_name).first()

        lint_commit = LintCommit(hash=commit,
                                 date=commit_info['date'],
                                 messages=commit_info['messages'],
                                 stats=commit_info['stats'])
        lint_commit.lint_id = lint.id

        self.session.add(lint_commit)
        self.session.commit()

    def insert_git(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            git_entry = Git(repository_name=repo_name, data=repo_info)
            self.session.add(git_entry)

        self.session.commit()
