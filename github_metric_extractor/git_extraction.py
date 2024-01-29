import pathlib
from pydriller import Repository

def _get_repositories(repositories: dict[str, str], clone_repo_to: str) -> dict[str, Repository]:
    """Creates Pydriller Repository generators for all repositories in a dictionary. When the generator is used, the repository will be cloned to the provided path.
    
    Keyword arguments:
    repositories -- dictionary with repo name as key and url (either path to repo or github address) as value
    clone_repo_to -- path to location where the repo will be stored

    Returns:
    A dictionary with repo name as key and the Pydriller Repository object as value.
    """
    base_path = pathlib.Path(clone_repo_to).absolute()

    if not base_path.exists():
        base_path.mkdir(parents=True)
    return {repo_name: _get_repository(repo_address, repo_name, clone_repo_to) for (repo_name, repo_address) in repositories.items()}

def _get_repository(repo_address: str, repo_name, clone_repo_to: str) -> Repository:
    """Get one Pydriller Repository"""
    repo_path = pathlib.Path(clone_repo_to + repo_name)

    if not repo_path.exists():
        return Repository(repo_address, clone_repo_to=clone_repo_to)
    return Repository(repo_path)

def _get_metrics(Repository: str) -> list[float]:
    # TODO: Implement extraciton of all metrict, structure the output etc...
    pass

def process_repositories(repositories: dict[str, str]) -> dict[str, list[float]]:
    metrics = {}
    repos = _get_repositories(repositories)

    for repo_name, repo in repos:
        metrics[repo_name] = _get_metrics(repo)

