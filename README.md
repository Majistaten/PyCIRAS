# PyCIRAS: Python Code Insight and Repository Analysis System

PyCIRAS (Python Code Insight and Repository Analysis System) is a comprehensive tool designed for mining, analyzing, and
visualizing data from Git repositories. This tool has been developed as part of a research study, and it is intended to
assist researchers and developers in extracting valuable insights from code repositories.

## Features

- Clone and manage multiple Git repositories.
- Extract metadata, unit testing data, and code quality metrics from repositories.
- Store raw data in an SQLite database or json, and process it into CSV files.
- Interactive data analysis and visualization using JupyterLab Notebooks.

## Contributors
  - [Tobias Hansson](https://github.com/Majistaten)
  - [Samuel Thand](https://github.com/SamuelThand)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Majistaten/PyCIRAS
cd PyCIRAS
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Requirements

- [Python](https://www.python.org/downloads/) 3.10 or higher
- [GitHub API token](https://github.com/settings/tokens) (optional, but needed for metadata and stargazer mining)

### Replication of study

1. Clone the reproduction package:

```bash
git clone https://github.com/Majistaten/PyCIRAS-reproduction-package
```

2. Unzip the content of the reproduction package into the `out/data` folder and ensure that the name of the folder
   is `2024-03-29_11-30`.
3. Start JupyterLab:

```bash
jupyter lab
```

4. Open and interact with the provided notebook `notebooks/thesis.ipynb` to conduct the data analysis and visualization.

### Jupyter Notebook demo

1. Start JupyterLab:

```bash
jupyter lab
```

2. Open the provided notebook `notebooks/DEMO.ipynb` to see a demonstration of the PyCIRAS tool.

### Custom usage

1. Start JupyterLab:

```bash
jupyter lab
```

2. Define the repositories to mine by either:
    - Entering the repository URLs in the `repos.txt` file, one line per URL.
    - Creating a list of repository URLs in a jupyter notebook. For example, change the content of the `repos` list in
      `notebooks/thesis.ipynb`.
3. Fine-tune the mining process by adjusting the content in the `utility/config.py` file.
4. Rename `.env.example` to `.env`.
5. (optional) Enter your GitHub API token and NTFY credentials in the `.env` file.
6. Clone the repositories:
```python
import pyciras
# Change the parameters according to your needs.
pyciras.run_repo_cloner(repo_urls=None,  # replace with the list of repository URLs if not using repos.txt
                        chunk_size=100,
                        multiprocessing=True)
```
7. Mine the repositories:
```python
import pyciras
# Change the parameters according to your needs.
pyciras.run_mining(repo_urls=None,  # replace with the list of repository URLs if not using repos.txt
                   chunk_size=1,
                   multiprocessing=False,
                   persist_repos=False,
                   stargazers=True,
                   metadata=True,
                   test=True,
                   git=True,
                   lint=True)
```
8. Create a new Jupyter notebook or make the needed changes in `notebooks/thesis.ipynb` and start analyzing the mined
   data.

## Modules

### Data_IO

This module is responsible for all I/O and data management. It consists of three submodules:

- `repo_management`: Handles cloning, storing, removing, and loading Git repositories for mining operations.
- `database_management`: Inserts raw data from mining operations into an SQLite database.
- `data_management`: Processes raw JSON data into a flat format and creates CSV files using the Pandas library.
- `database_models`: Contains the SQLAlchemy models for the SQLite database.

### Mining

This module is responsible for mining repositories and extracting data:

- `git_mining`: Provides metadata mining through GitHub's API and Git process mining with Pydriller.
- `test_mining`: Uses an abstract syntax tree traversal module to mine unit testing data.
- `lint_mining`: Mines code quality data through Pylint.

### Notebooks

This module contains JupyterLab Notebooks, which combine Python code, equations, documentation, and visualizations.
These notebooks facilitate interactive experimentation and data analysis using libraries like NumPy, SciPy, Matplotlib,
and Seaborn.

The main notebook is `thesis.ipynb`, which is used to replicate the study's results. It contains the data analysis and
visualization code for the study.

### Utility

This module contains utility functions and configurations for the PyCIRAS tool:

- `config`: Contains configurations for the mining process, such as directory structures, ignore directories, logging, and result formats.
- `logger_setup`: Configures the logging system for the tool.
- `ntfyer`: Sends notifications to the user using the NTFY library.
- `progress_bars`: Provides progress bars for the mining process.
- `utils`: Contains utility functions for the tool.
- `timer`: Decorator for timing function execution times.

## Reproduction Package

The reproduction package for this study can be cloned
from [PyCIRAS-reproduction-package](https://github.com/Majistaten/PyCIRAS-reproduction-package). This package includes
the datasets and additional materials required to reproduce the study's results.
