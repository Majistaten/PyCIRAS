import config
import json
from datetime import datetime
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def create_timestamped_data_directory() -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = ROOT_PATH / config.OUTPUT_FOLDER / config.DATA_FOLDER / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def write_pydriller_metrics_to_json(data: dict, path: Path):
    data_path = path / 'pydriller_metrics.json'
    with open(str(data_path), 'w') as file:
        json.dump(data, file, indent=4)


def write_pylint_metrics_to_json(data: dict, path: Path):
    data_path = path / 'pylint_metrics.json'
    with open(str(data_path), 'w') as file:
        json.dump(data, file, indent=4, cls=CustomEncoder)
