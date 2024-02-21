import sys
import venv
import subprocess
from pathlib import Path
import logging
import os
from tqdm import tqdm

venv_folder_name = '/venv'


def create_venv(repository_root: Path) -> None:
    target_folder = repository_root / 'venv'
    venv.create(target_folder, with_pip=True)
    logging.info(f'created venv at {target_folder}')


def get_venv_executable_path(repository_root: Path) -> Path:
    if sys.platform == 'win32':
        path = repository_root / venv_folder_name / 'Scripts' / 'python.exe'
        if path.exists():
            return path
        else:
            logging.error(f'Could not find venv {repository_root}')
            raise FileNotFoundError(f'Python file not found at: {path}')
    else:
        path = repository_root / venv_folder_name / 'bin' / 'python'
        if path.exists():
            return path
        else:
            logging.error(f'Could not find venv {repository_root}')
            raise FileNotFoundError(f'Python file not found at: {path}')


def install_requirements(venv_python_path: Path, requirements_path: Path) -> None:
    logging.info(f'Installing requirements from {requirements_path} into {venv_python_path}')
    subprocess.run([str(venv_python_path), '-m', 'pip', 'install', '-r', str(requirements_path)], check=True)


def prepare_repository_venv(repository_root: Path):
    create_venv(repository_root)
    venv_path = get_venv_executable_path(repository_root)
    install_requirements(venv_path, repository_root / 'requirements.txt')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    repositories_folder = Path('../repositories').absolute()
    children = [folder for folder in repositories_folder.iterdir() if folder.is_dir()]
    print(f'Found {len(children)}')
    print(f'Folders: {children}')
    logging.info(f'Preparing repositories.')
    for folder in tqdm(children):
        prepare_repository_venv(folder)

    logging.info(f'Finished preparing repositories.')
