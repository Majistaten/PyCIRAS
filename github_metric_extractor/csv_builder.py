from pathlib import Path
import csv
import json
from datetime import datetime

test_dictionary = {
    "..\\repositories\\conala-baseline": {
        "total_commits": 24,
        "commits": [
            {
                "commit_hash": "7deff169c3e3b690fd9b0df5f9b939cac0fa0632",
                "commit_date": "2018-06-03 02:38:59-04:00"
            },
            {
                "commit_hash": "f36eef31cbb4752a309043dc642ca26ee936d806",
                "commit_date": "2018-06-03 02:53:21-04:00"
            }
        ],
        "developers": [
            "Graham Neubig",
            "Edgar Chen",
            "Bernhard Stadler"
        ],
        "developer_count": 3,
        "lines_added": 1296,
        "code_churn": {
            "total": {
                "setup.cfg": 40,
                "setup.py": 12,
            },
            "max": {
                "setup.cfg": 40,
                "setup.py": 12,
            },
            "avg": {
                "setup.cfg": 40,
                "setup.py": 12,
            }
        }
    }
}


def flatten_json(json, prefix=''):
    """
    Flatten a nested JSON object recursively. Add a prefix to each key to indicate the level of nesting.
    """

    # TODO vi ska ladda JSON från en fil - vad ska komma in i denna funktion? Laddas det som dictionary? JSON object?

    print(json)

    # out = {}
    #
    # def flatten(data, name=''):
    #     if type(data) is dict:
    #         for nested_data in data:
    #             flatten(data[nested_data], name + nested_data + '_')
    #     elif type(data) is list:
    #         i = 0
    #         for nested_data in data:
    #             flatten(nested_data, name + str(i) + '_')
    #             i += 1
    #     else:
    #         out[name[:-1]] = data
    #
    # flatten(json, prefix)
    # return out
    return


def json_to_csv(json_data, csv_file_name):
    """
    Convert a list of JSON objects to a CSV file and save it in a specified directory using pathlib.

    :param json_data: List of JSON objects.
    :param output_directory: Directory where the CSV file will be saved, as a Path object.
    :param csv_file_name: Name of the CSV file.

    """
    # if not json_data:
    #     print("No data to write.")
    #     return
    #
    # timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    # output_directory = Path(__file__).parent.parent / 'csv' / f"./{timestamp}"
    #
    # # Ensure the output directory exists
    # output_directory.mkdir(parents=True, exist_ok=True)
    #
    # # Full path for the CSV file
    # csv_file_path = output_directory / csv_file_name
    #
    # # TODO logic for flattening the CSV and writing to files
    # headers = json_data.keys()

    flatten_json(json.dumps(test_dictionary, indent=4))


def read_json_from_file(file_path):
    """
    Read JSON data from a file using pathlib.

    :param file_path: Path to the JSON file, as a Path object.
    :return: A list of JSON objects.
    """
    with file_path.open('r', encoding='utf-8') as file:
        return json.load(file)


if __name__ == "__main__":
    json_file_path = Path('test_out.json')
    csv_file_name = 'Pydriller.csv'

    json_data = read_json_from_file(json_file_path)
    json_to_csv(json_data, csv_file_name)
