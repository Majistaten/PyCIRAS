from pathlib import Path
import csv
import json


def json_to_csv(json_data, output_directory, csv_file_name):
    """
    Convert a list of JSON objects to a CSV file and save it in a specified directory using pathlib.

    :param json_data: List of JSON objects.
    :param output_directory: Directory where the CSV file will be saved, as a Path object.
    :param csv_file_name: Name of the CSV file.
    """
    # Ensure json_data is not empty
    if not json_data:
        print("No data to write.")
        return

    # Ensure the output directory exists
    output_directory.mkdir(parents=True, exist_ok=True)

    # Full path for the CSV file
    csv_file_path = output_directory / csv_file_name

    headers = json_data.keys()

    # TODO logic for flattening the CSV and writing to files




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
    csv_file_name = 'test_csv.csv'

    # Define the output directory one level up and inside a new "csv" folder
    output_directory = Path(__file__).parent.parent / 'csv'

    json_data = read_json_from_file(json_file_path)
    json_to_csv(json_data, output_directory, csv_file_name)
