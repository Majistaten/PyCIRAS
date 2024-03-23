import os
from datetime import datetime
from typing import (
    Any,
    Iterable,
    List, Optional,
    Union,
)

from git import RemoteProgress, Repo
from pydriller import Repository
from rich.progress import Progress, ProgressColumn, Task, TextColumn

from pyciras import logger


# TODO implementera disable


class RepositoryWithProgress(Repository):

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

        def _clone_remote_repo(self, tmp_folder: str, repo: str) -> str:
            repo_folder = os.path.join(tmp_folder, self._get_repo_name_from_url(repo))
            if os.path.isdir(repo_folder):
                logger.info(f"Reusing folder {repo_folder} for {repo}")
            else:
                logger.info(f"Cloning {repo} in temporary folder {repo_folder}")

                Repo.clone_from(url=repo,
                                to_path=repo_folder,
                                progress=GitProgress(progress, description=repo))

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
            completed=cur_count
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
                                     completed=self.progress.tasks[self.task_id].total)
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
