import concurrent.futures
import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Generator, Iterable,
    List, Optional,
    Union,
)

from git import RemoteProgress, Repo
from pydriller import Commit, Repository
from pydriller.git import Git
from rich.progress import Progress, ProgressColumn, Task, TextColumn


# TODO implementera disable

class RepositoryWithProgress(Repository):
    """Overrides the traverse_commits method to show a progress bar, and removes INFO level logs."""

    def __init__(self, path_to_repo: Union[str, List[str]], single: Optional[str] = None,
                 since: Optional[datetime] = None, since_as_filter: Optional[datetime] = None,
                 to: Optional[datetime] = None, from_commit: Optional[str] = None, to_commit: Optional[str] = None,
                 from_tag: Optional[str] = None, to_tag: Optional[str] = None, include_refs: bool = False,
                 include_remotes: bool = False, num_workers: int = 1, only_in_branch: Optional[str] = None,
                 only_modifications_with_file_types: Optional[List[str]] = None, only_no_merge: bool = False,
                 only_authors: Optional[List[str]] = None, only_commits: Optional[List[str]] = None,
                 only_releases: bool = False, filepath: Optional[str] = None, include_deleted_files: bool = False,
                 histogram_diff: bool = False, skip_whitespaces: bool = False, clone_repo_to: Optional[str] = None,
                 order: Optional[str] = None, progress: Progress = None):

        super().__init__(path_to_repo, single, since, since_as_filter, to, from_commit, to_commit, from_tag, to_tag,
                         include_refs, include_remotes, num_workers, only_in_branch, only_modifications_with_file_types,
                         only_no_merge, only_authors, only_commits, only_releases, filepath, include_deleted_files,
                         histogram_diff, skip_whitespaces, clone_repo_to, order)

        self.progress = progress

    def traverse_commits(self) -> Generator[Commit, None, None]:
        """
        Analyze all the specified commits (all of them by default), returning
        a generator of commits.
        """
        for path_repo in self._conf.get('path_to_repos'):
            with self._prep_repo(path_repo=path_repo) as git:
                # Get the commits that modified the filepath. In this case, we can not use
                # git rev-list since it doesn't have the option --follow, necessary to follow
                # the renames. Hence, we manually call git log instead
                if self._conf.get('filepath') is not None:
                    self._conf.set_value(
                        'filepath_commits',
                        git.get_commits_modified_file(self._conf.get('filepath'),
                                                      self._conf.get('include_deleted_files'))
                    )

                # Gets only the commits that are tagged
                if self._conf.get('only_releases'):
                    self._conf.set_value('tagged_commits', git.get_tagged_commits())

                # Build the arguments to pass to git rev-list.
                rev, kwargs = self._conf.build_args()

                with concurrent.futures.ThreadPoolExecutor(max_workers=self._conf.get("num_workers")) as executor:
                    for job in executor.map(self._iter_commits, git.get_list_commits(rev, **kwargs)):

                        for commit in job:
                            yield commit

    @contextmanager
    def _prep_repo(self, path_repo: str) -> Generator[Git, None, None]:
        local_path_repo = path_repo
        if self._is_remote(path_repo):
            local_path_repo = self._clone_remote_repo(self._clone_folder(), path_repo)
        local_path_repo = str(Path(local_path_repo).expanduser().resolve())

        # when multiple repos are given in input, this variable will serve as a reminder
        # of which one we are currently analyzing
        self._conf.set_value('path_to_repo', local_path_repo)

        self.git = Git(local_path_repo, self._conf)
        # saving the Git object for further use
        self._conf.set_value("git", self.git)

        # checking that the filters are set correctly
        self._conf.sanity_check_filters()
        yield self.git

        # cleaning, this is necessary since GitPython issues on memory leaks
        self._conf.set_value("git", None)
        self.git.clear()
        self.git = None  # type: ignore

        # delete the temporary directory if created
        if self._is_remote(path_repo) and self._cleanup is True:
            assert self._tmp_dir is not None
            try:
                self._tmp_dir.cleanup()
            except (PermissionError, OSError):
                # On Windows there might be cleanup errors.
                # Manually remove files
                shutil.rmtree(self._tmp_dir.name, ignore_errors=True)

    def _clone_remote_repo(self, tmp_folder: str, repo: str) -> str:
        repo_folder = os.path.join(tmp_folder, self._get_repo_name_from_url(repo))

        Repo.clone_from(url=repo,
                        to_path=repo_folder,
                        progress=GitProgress(self.progress, description=repo))

        return repo_folder


class GitProgress(RemoteProgress):
    """Feeds progress info from git to a Progress instance"""

    OP_CODES = [
        "BEGIN",
        "CHECKING_OUT",
        "COMPRESSING",
        "COUNTING",
        "END",
        "FINDING_SOURCES",
        "RECEIVING",
        "RESOLVING",
        "WRITING",
    ]

    OP_CODE_MAP = {
        getattr(RemoteProgress, _op_code): _op_code for _op_code in OP_CODES
    }

    def __init__(self,
                 progress: Progress,
                 description: str = "Repository"):
        super().__init__()
        self.progress = progress
        self.description = description
        self.current_operation = None
        self.task_ids = {}

    @classmethod
    def get_curr_op(cls, op_code: int) -> str:
        """Get OP name from OP code."""
        op_code_masked = op_code & cls.OP_MASK
        return cls.OP_CODE_MAP.get(op_code_masked, "?").title()

    def update(
            self,
            op_code: int,
            cur_count: Union[str, float],
            max_count: Union[str, float, None] = None,
            message: str = "",
    ) -> None:

        """Update the progress instance with the current operation."""

        self.current_operation = self.get_curr_op(op_code)

        if op_code & self.BEGIN:
            self.task_ids[self.current_operation] = self.progress.add_task(
                description=f"{self.current_operation} {self.description}",
                total=max_count
            )

        self.progress.update(
            task_id=self.task_ids[self.current_operation],
            completed=cur_count,
            refresh=True
        )

        if op_code & self.END:
            self.progress.stop_task(self.task_ids[self.current_operation])
            self.progress.remove_task(self.task_ids[self.current_operation])


class IterableProgressWrapper:
    """Allows the iterable to be used in a for loop with progress tracking."""

    def __init__(self,
                 iterable: Iterable[Any],
                 progress: Progress,
                 description: str = "Processing",
                 completion_description: Optional[str] = None,
                 type: str = "iterable",
                 postfix: str = "") -> None:
        self.iterable = iterable
        self.progress = progress
        self.description = description
        self.completion_description = completion_description
        self.postfix = postfix
        self.type = type
        self.iterable_iterator = iter(iterable)
        self.total_steps = len(iterable) if hasattr(iterable, '__len__') else None
        self.task_id = progress.add_task(self.description,
                                         total=self.total_steps,
                                         type=self.type,
                                         postfix=self.postfix)

    def __iter__(self):
        return self

    def __next__(self):

        try:
            item = next(self.iterable_iterator)
            self.progress.advance(self.task_id)  # TODO update med refresh=True?
            return item

        except StopIteration:

            if self.completion_description:
                self.progress.update(self.task_id,
                                     description=f"[green]{self.completion_description}",
                                     completed=self.progress.tasks[self.task_id].total,
                                     refresh=True)
            self.progress.stop_task(self.task_id)
            self.progress.remove_task(self.task_id)

            raise


class IterableColumn(ProgressColumn):
    """A custom column for displaying iterable progress. Only visible when the task is an iterable."""

    def render(self, task: Task):
        """Render the column."""

        if task.fields.get("type") == "iterable":

            completed = int(task.completed)
            total = task.total
            postfix = task.fields.get("postfix", "")
            completion_description = task.fields.get("completion_description", "")

            if total is not None:
                progress_text = f"{completed}/{int(total)}"

            else:
                progress_text = f"{completed}/?"

            if task.finished and completion_description:
                return TextColumn(f"[green]{completion_description} {postfix}").render(task)

            else:
                return TextColumn(f"{progress_text} {postfix}").render(task)

        else:
            return TextColumn("").render(task)
