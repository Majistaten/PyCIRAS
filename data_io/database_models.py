from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.orm import declarative_base, relationship

# Define the base class for the database schema
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
    test_commits = relationship('TestCommit', back_populates='test')


class TestCommit(Base):
    __tablename__ = 'test_commits'
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('tests.id'))
    test = relationship("Test", back_populates="test_commits")
    hash = Column(String)
    files = Column(JSON)
    test_to_code_ratio = Column(Float)
    date = Column(String)


class Lint(Base):
    __tablename__ = 'lints'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="lints")


class LintCommit(Base):
    __tablename__ = 'lint_commits'
    id = Column(Integer, primary_key=True)
    lint_id = Column(Integer, ForeignKey('lints.id'))
    hash = Column(String)
    messages = Column(JSON)
    stats = Column(JSON)
    date = Column(String)


# class LintMessages(Base):
#     __tablename__ = 'lint_messages'
#     id = Column(Integer, primary_key=True)
#     lint_commit_id = Column(Integer, ForeignKey('lint_commits.id'))
#     lint_commit = relationship("LintCommit", back_populates="messages")
#     data = Column(JSON)
#
#
# class LintStats(Base):
#     __tablename__ = 'lint_stats'
#     id = Column(Integer, primary_key=True)
#     lint_commit_id = Column(Integer, ForeignKey('lint_commits.id'))
#     lint_commit = relationship("LintCommit", back_populates="stats")
#     data = Column(JSON)


class Git(Base):
    __tablename__ = 'gits'
    id = Column(Integer, primary_key=True)
    repository_name = Column(String, ForeignKey('repositories.repo_name'))
    repository = relationship("Repository", back_populates="gits")
    data = Column(JSON)