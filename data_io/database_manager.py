import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_io.data_management import CustomEncoder
from utility import config, dummy_data
from data_io.database_models import Base, Repository, Metadata, Stargazers, Test, Git, TestCommit, Lint, LintCommit


class DatabaseManager:
    def __init__(self, database_path: Path):
        self.engine = create_engine(f'sqlite:///{database_path}', echo=False)
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

            json_repo_info = json.dumps(repo_info, cls=CustomEncoder)
            metadata_entry = Metadata(repository_name=repo_name, data=json_repo_info)
            self.session.add(metadata_entry)

        self.session.commit()

    def insert_stargazers(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            json_repo_info = json.dumps(repo_info, cls=CustomEncoder)
            stargazers_entry = Stargazers(repository_name=repo_name, data=json_repo_info)
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

        files = json.dumps(commit_info['files'], cls=CustomEncoder)
        test_commit = TestCommit(hash=commit,
                                 files=files,
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

        messages = json.dumps(commit_info['messages'], cls=CustomEncoder)
        stats = json.dumps(commit_info['stats'], cls=CustomEncoder)
        lint_commit = LintCommit(hash=commit,
                                 date=commit_info['date'],
                                 messages=messages,
                                 stats=stats)
        lint_commit.lint_id = lint.id

        self.session.add(lint_commit)
        self.session.commit()

    def insert_git(self, data: dict):
        for repo_name, repo_info in data.items():
            repository = self.session.query(Repository).filter_by(repo_name=repo_name).first()
            if not repository:
                repository = Repository(repo_name=repo_name)
                self.session.add(repository)

            json_repo_info = json.dumps(repo_info, cls=CustomEncoder)
            git_entry = Git(repository_name=repo_name, data=json_repo_info)
            self.session.add(git_entry)

        self.session.commit()


# Example usage:
if __name__ == "__main__":

    with DatabaseManager(config.OUTPUT_FOLDER / 'database.db') as dbm:
        dbm.insert_metadata(data=dummy_data.metadata)
        dbm.insert_stargazers(data=dummy_data.stargazers)
        dbm.insert_tests(data=dummy_data.test)
        dbm.insert_git(data=dummy_data.git)
        dbm.insert_lints(data=dummy_data.lint)

