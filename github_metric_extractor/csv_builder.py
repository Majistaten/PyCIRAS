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

    # Determine the CSV column headers from the keys of the first JSON object
    # headers = json_data[0].keys()
    headers = json_data.keys()

    # TODO only works for flat JSON, need to flatten the data.
    # TODO Check Pandas or something
    # Writing to CSV
    with csv_file_path.open(mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        # for data in json_data:
        for item in json_data:
            # Ensure item is a non-empty string that should contain JSON
            if isinstance(item, str) and item.strip():
                try:
                    data = json.loads(item)
                    writer.writerow(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e.msg} at line {e.lineno} column {e.colno}")
            else:
                # If item is already a dictionary or not a valid JSON string, handle accordingly
                if isinstance(item, dict):
                    writer.writerow(item)
                else:
                    print("Item is not a valid JSON string:", item)


def read_json_from_file(file_path):
    """
    Read JSON data from a file using pathlib.

    :param file_path: Path to the JSON file, as a Path object.
    :return: A list of JSON objects.
    """
    with file_path.open('r', encoding='utf-8') as file:
        return json.load(file)


if __name__ == "__main__":
    json_file_path = Path('test_out.json')  # Update this path
    csv_file_name = 'test_csv.csv'  # Define your CSV file name

    # Define the output directory one level up and inside a new "csv" folder
    output_directory = Path(__file__).parent.parent / 'csv'

    json_data = read_json_from_file(json_file_path)
    json_to_csv(json_data, output_directory, csv_file_name)
