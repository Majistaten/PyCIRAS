from git import RemoteProgress
from rich import progress, console
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, ProgressColumn, TimeElapsedColumn, \
    SpinnerColumn, TaskProgressColumn


class RichProgressColumn(ProgressColumn):
    """ A custom column to display as 'current/total'."""

    def render(self, task):
        if task.total is not None:
            return TextColumn(f"{int(task.completed)}/{int(task.total)}").render(task)
        else:
            return TextColumn(f"{int(task.completed)}/?").render(task)


class RichIterableProgressBar:
    """ A progress bar for an iterable that uses the rich library.

    Args:
        iterable: The iterable to iterate over.
        description: The description of the process.
        completion_description: The description of the process upon completion.
        postfix: A postfix to add to the progress bar.
        bar_width: The width of the progress bar.
        transient: Whether the progress bar is transient.
        refresh_per_second: The refresh rate of the progress bar.
        disable: Whether the progress bar is disabled.
    """

    def __init__(self,
                 iterable,
                 description: str = "Processing",
                 completion_description: str | None = None,
                 postfix: str | None = None,
                 bar_width: int = 40,
                 transient: bool = False,
                 refresh_per_second: float = 10,
                 disable: bool = False):
        """Initialize a progress bar with an iterable."""
        self.iterable = iterable
        self.description = description
        self.completion_description = completion_description
        self.postfix = postfix
        self.bar_width = bar_width
        self.transient = transient
        self.refresh_per_second = refresh_per_second
        self.disable = disable
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(bar_width=self.bar_width),
            RichProgressColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            TextColumn(f"[green]{self.postfix}" if self.postfix else ""),
            transient=self.transient,
            refresh_per_second=self.refresh_per_second,
            disable=self.disable,
            console=console.Console(),
        )
        self.task = None
        self.iterable_iterator = iter(self.iterable)

    def __iter__(self):
        """Start the progress bar and return the iterator."""
        total_steps = len(self.iterable) if hasattr(self.iterable, '__len__') else None
        self.task = self.progress.add_task(f"[green]{self.description}...", total=total_steps)
        self.progress.start()
        return self

    def __next__(self):
        """Advance the progress bar."""
        try:
            item = next(self.iterable_iterator)
            self.progress.advance(self.task)
            return item
        except StopIteration:
            if self.completion_description:
                self.progress.update(self.task, description=f"[green]{self.completion_description}",
                                     completed=self.progress.tasks[self.task].total)

            self.progress.stop()
            raise


class CloneProgress(RemoteProgress):
    """Progressbar for git cloning process.

    Args:
        description: The description of the process.
        completion_description: The description of the process upon completion.
        postfix: A postfix to add to the progress bar.
        bar_width: The width of the progress bar.
        transient: Whether the progress bar is transient.
        refresh_per_second: The refresh rate of the progress bar.
        disable: Whether the progress bar is disabled.
    """
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

    def __init__(self, description: str = "Processing",
                 completion_description: str | None = None,
                 postfix: str | None = None,
                 bar_width: int = 40,
                 transient: bool = False,
                 refresh_per_second: float = 10,
                 disable: bool = False) -> None:
        super().__init__()
        self.description = description
        self.completion_description = completion_description
        self.postfix = postfix
        self.bar_width = bar_width
        self.transient = transient
        self.refresh_per_second = refresh_per_second
        self.disable = disable
        self.curr_op = None
        self.progressbar = progress.Progress(
            progress.SpinnerColumn(),
            progress.TextColumn("[green]{task.description}"),
            progress.BarColumn(bar_width=self.bar_width),
            RichProgressColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            progress.TextColumn("{task.fields[message]}"),
            TextColumn(f"[green]{self.postfix}" if self.postfix else ""),
            console=console.Console(),
            transient=self.transient,
            refresh_per_second=self.refresh_per_second,
            disable=self.disable,
        )
        self.progressbar.start()
        self.active_task = None

    def __del__(self) -> None:
        self.progressbar.stop()

    @classmethod
    def get_curr_op(cls, op_code: int) -> str:
        """Get OP name from OP code."""
        op_code_masked = op_code & cls.OP_MASK
        return cls.OP_CODE_MAP.get(op_code_masked, "?").title()

    def update(
            self,
            op_code: int,
            cur_count: str | float,
            max_count: str | float | None = None,
            message: str | None = "",
    ) -> None:
        if op_code & self.BEGIN:
            self.curr_op = self.get_curr_op(op_code)
            self.active_task = self.progressbar.add_task(
                description=f"[green]{self.curr_op} {self.description}",
                total=max_count,
                message=f"[blue]message",
            )

        self.progressbar.update(
            task_id=self.active_task,
            completed=cur_count,
            message=f"[blue]{message}",
        )

        if op_code & self.END:
            self.progressbar.update(
                task_id=self.active_task,
                message=f"[bright_black]{message}",
            )
