from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn, ProgressColumn, TimeElapsedColumn, \
    SpinnerColumn, TaskProgressColumn


class RichProgressColumn(ProgressColumn):
    # A custom column to display as 'current/total'.
    def render(self, task):
        if task.total is not None:
            return TextColumn(f"{int(task.completed)}/{int(task.total)}").render(task)
        else:
            return TextColumn(f"{int(task.completed)}/?").render(task)


class RichIterableProgressBar:
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
            BarColumn(bar_width=self.bar_width, pulse_style='bar.pulse'),
            RichProgressColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            TextColumn(f"[green]{self.postfix}" if self.postfix else ""),
            transient=self.transient,
            refresh_per_second=self.refresh_per_second,
            disable=self.disable,
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


# Example usage
if __name__ == "__main__":
    import time

    def generate_items(n):
        for i in range(n):
            time.sleep(0.1)
            yield i

    items = range(50)
    for item in RichIterableProgressBar(items, description="Processing Items",
                                        completion_description="Completed processing",
                                        postfix="Name or something",
                                        bar_width=30,
                                        transient=False):
        time.sleep(0.1)

    generator = generate_items(30)
    for item in RichIterableProgressBar(generator, description="Processing Generator", transient=False):
        pass
