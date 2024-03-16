from utility import config, util
from pathlib import Path
import csv
import json
from datetime import datetime
import data_io.data_manipulation as data_converter
import pandas as pd


class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle sets and datetime objects."""

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)  # Convert sets to lists
        elif isinstance(obj, datetime):
            return str(obj)
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def create_timestamped_data_directory() -> Path:
    """Creates a timestamped directory for the output data."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_directory = config.DATA_FOLDER / f'./{timestamp}'
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def write_json_data(data: dict, path: Path):
    """Loads existing JSON data and updates it with new data, or writes new data to a JSON file."""
    try:
        with open(path, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError:
        existing_data = {}

    existing_data.update(data)

    with open(path, 'w') as file:
        json.dump(existing_data, file, indent=4, cls=CustomEncoder)


# TODO Refactor?
def pydriller_data_csv(data: dict, path: Path):
    """Writes Pydriller data to a CSV file."""
    _write_to_csv(data, path / 'pydriller-flat.csv', None)


def pylint_data_csv(data: dict, path: Path):
    """Writes Pylint data to a CSV file using pandas."""

    for repo, dates in data.items():
        data_rows = []
        for date, pylint_data in dates.items():
            row = {'date': date, **pylint_data}
            data_rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(data_rows)

        # Convert 'date' column to datetime and sort
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df.sort_values(by='date', inplace=True)

        # Ensure 'date' and 'commit_hash' are the first two columns, sort other columns alphabetically
        fixed_columns = ['date', 'commit_hash']
        other_columns = sorted([col for col in df.columns if col not in fixed_columns])
        df = df[fixed_columns + other_columns]

        df = df.astype(str).replace('nan', 'NaN')

        df.to_csv(path / f'pylint-{repo}.csv', index=False)

# TODO denna funktionen uppdaterar global note värden på nåt sätt så de inte blir korrekt om man jämför med raw data
# TODO sker bara vid parallellkörning
# def pylint_data_csv(data: dict, path: Path):
#     """Writes Pylint data to a CSV file."""
#     for key, value in data.items():
#         output_path = path / f"pylint-{util.get_repo_name_from_path(key)}.csv"
#         if value.values() is None:
#             continue
#         _write_to_csv(value, output_path, insert_key_as="date")


def _write_to_csv(data: dict, path: Path, insert_key_as: str | None) -> None:
    """Writes the data to a CSV file."""
    formatted_data = data_converter.dict_to_list(data, insert_key_as)
    with open(path, 'a', newline='') as file:
        field_names = set()
        for section in formatted_data:
            field_names.update([k for k in section.keys()])

        field_names = sorted(field_names)

        writer = csv.DictWriter(file, fieldnames=field_names, restval="NaN")
        if path.stat().st_size == 0:
            writer.writeheader()
        writer.writerows(formatted_data)


def stargazers_data_csv(data: dict, path: Path) -> None:
    """Writes stargazers over time to a CSV file."""

    # Determine all unique repositories to establish the columns (other than the DATE column)
    repos = set()
    for day_data in data.values():
        repos.update(day_data.keys())
    repos = sorted(repos)  # Sort repositories for consistent column order

    with open(path / 'stargazers-over-time.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow(['date'] + repos)

        # Write data for each date
        for date, data in data.items():
            row = [date] + [data.get(repo, 0) for repo in repos]
            writer.writerow(row)


def unit_testing_data_csv(data: dict, path: Path) -> None:
    """Writes/updates unit testing data to/in a CSV file."""

    file_path = path / 'test-to-code-ratio-over-time.csv'

    # Try to load the existing CSV into a DataFrame or create an empty one if the file doesn't exist
    try:
        existing_df = pd.read_csv(file_path, index_col='date', parse_dates=True)
    except FileNotFoundError:
        existing_df = pd.DataFrame()

    # Preparing new data from the incoming dictionary
    new_data = []
    for repo, timestamps in data.items():
        for timestamp, details in timestamps.items():
            new_data.append({
                'date': timestamp,
                repo: details.get('test-to-code-ratio')
            })

    # Create a new DataFrame from the new data
    new_df = pd.DataFrame(new_data)
    new_df['date'] = pd.to_datetime(new_df['date'], utc=True)
    new_df.set_index('date', inplace=True)

    # Merge or update the existing data with the new data
    if not existing_df.empty:
        updated_df = pd.merge(existing_df, new_df, left_index=True, right_index=True, how='outer')
    else:
        updated_df = new_df
    updated_df = updated_df.reindex(sorted(updated_df.columns), axis=1)

    # Sort dates from oldest to newest
    updated_df.sort_index(inplace=True)

    # Replace 'nan' with 'NaN'
    updated_df = updated_df.astype(str).replace('nan', 'NaN')

    # Write the updated DataFrame
    updated_df.to_csv(file_path)

