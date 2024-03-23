# Import necessary modules
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from utility import config

# Define the base class
Base = declarative_base()


class Repository(Base):
    __tablename__ = 'repositories'
    repo_name = Column(String, primary_key=True)
    repo_metadata = relationship('Metadata', back_populates='repository', uselist=False)
    tests = relationship('Test', back_populates='repository')
    lints = relationship('Lint', back_populates='repository')
    stargazers = relationship('Stargazers', back_populates='repository')
    gits = relationship('Git', back_populates='repository')


class Metadata(Base):
    __tablename__ = 'metadata'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="repo_metadata")
    data = Column(JSON)


class Stargazers(Base):
    __tablename__ = 'stargazers'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="stargazers")
    data = Column(JSON)


class Test(Base):
    __tablename__ = 'tests'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="tests")
    files = Column(JSON)
    test_to_code_ratio = Column(Float)
    date = Column(DateTime)


class Lint(Base):
    __tablename__ = 'lints'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="lints")


class LintCommit(Base):
    __tablename__ = 'lint_commits'
    id = Column(Integer, primary_key=True)
    lint_id = Column(Integer, ForeignKey('lints.id'))
    messages_id = Column(Integer, ForeignKey('lint_messages.id'))
    stats_id = Column(Integer, ForeignKey('lint_stats.id'))
    date = Column(DateTime)


class LintMessages(Base):
    __tablename__ = 'lint_messages'
    id = Column(Integer, primary_key=True)
    data = Column(JSON)


class LintStats(Base):
    __tablename__ = 'lint_stats'
    id = Column(Integer, primary_key=True)
    data = Column(JSON)


class Git(Base):
    __tablename__ = 'gits'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="gits")
    data = Column(JSON)


def create_session(database_path: str):
    engine = create_engine(f'sqlite:///{database_path}', echo=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    return session()


def insert_metadata(database_path: Path, data: dict):
    session = create_session(database_path)

    for repo_name, repo_info in data.items():
        repository = session.query(Repository).filter_by(repo_name=repo_name).first()
        if not repository:
            repository = Repository(repo_name=repo_name)
            session.add(repository)

        metadata_entry = Metadata(repository_name=repo_name, data=repo_info)
        session.add(metadata_entry)

    session.commit()
    session.close()


# Example usage:
if __name__ == "__main__":
    # Define your JSON data here
    json_data = {
        "TDD-Hangman": {
            "createdAt": "2023-10-07T10:24:24Z",
            "pushedAt": "2023-10-07T10:25:13Z",
            "updatedAt": "2023-10-07T10:25:20Z",
            "archivedAt": None,
            "description": "This is a simple hangman game. It was built collaboratively using test-driven development, Kanban methodology and Git feature branch workflow, with pull requests and peer reviews.",
            "forkCount": 0,
            "stargazerCount": 0,
            "hasDiscussionsEnabled": False,
            "hasIssuesEnabled": True,
            "hasProjectsEnabled": True,
            "hasSponsorshipsEnabled": False,
            "fundingLinks": [],
            "hasWikiEnabled": True,
            "homepageUrl": None,
            "isArchived": False,
            "isEmpty": False,
            "isFork": False,
            "isInOrganization": False,
            "isLocked": False,
            "isMirror": False,
            "isPrivate": False,
            "isTemplate": False,
            "licenseInfo": None,
            "lockReason": None,
            "visibility": "PUBLIC",
            "url": "https://github.com/SamuelThand/TDD-Hangman",
            "owner": {
                "login": "SamuelThand"
            },
            "resourcePath": "/SamuelThand/TDD-Hangman",
            "diskUsage": 261,
            "languages": {
                "nodes": [
                    {
                        "name": "Python"
                    }
                ]
            },
            "primaryLanguage": {
                "name": "Python"
            }
        },
        "TDD-String-Calculator": {
            "createdAt": "2023-10-07T10:24:24Z",
            "pushedAt": "2023-10-07T10:25:13Z",
            "updatedAt": "2023-10-07T10:25:20Z",
            "archivedAt": None,
            "description": "This is a simple string calculator. It was built collaboratively using test-driven development, Kanban methodology and Git feature branch workflow, with pull requests and peer reviews.",
            "forkCount": 0,
            "stargazerCount": 0,
            "hasDiscussionsEnabled": False,
            "hasIssuesEnabled": True,
            "hasProjectsEnabled": True,
            "hasSponsorshipsEnabled": False,
            "fundingLinks": [],
            "hasWikiEnabled": True,
            "homepageUrl": None,
            "isArchived": False,
            "isEmpty": False,
            "isFork": False,
            "isInOrganization": False,
            "isLocked": False,
            "isMirror": False,
            "isPrivate": False,
            "isTemplate": False,
            "licenseInfo": None,
            "lockReason": None,
            "visibility": "PUBLIC",
            "url": "https://github.com/SamuelThand/TDD-String-Calculator",
            "owner": {
                "login": "SamuelThand"
            },
            "resourcePath": "/SamuelThand/TDD-String-Calculator",
            "diskUsage": 261,
            "languages": {
                "nodes": [
                    {
                        "name": "Python"
                    }
                ]
            },
            "primaryLanguage": {
                "name": "Python"
            }
        }
    }

    # Define the path to your database file
    db_path = Path(config.OUTPUT_FOLDER / 'repositories.db')

    # Call the function to insert data
    insert_metadata(database_path=db_path, data=json_data)
