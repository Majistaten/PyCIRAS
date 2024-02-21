import pydriller
import logging

# Create or get the root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set the debug level for the logger

# Create a file handler for writing logs to a file
file_handler = logging.FileHandler('test_mining_log_2020.log')
file_handler.setLevel(logging.DEBUG)  # Set the debug level for the file handler
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create a console handler for printing logs to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set the debug level for the console handler
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logging.addLevelName(logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))

with open('test_mining_result_round2.txt', 'w') as output_file:
    with open('test_mining_repos_round2.txt', 'r') as file:
        lines = file.readlines()

        for line in lines:
            line = line.strip()
            commit_count = 0
            first_commit_date = None
            last_commit_date = None

            try:
                for commit in pydriller.Repository(line).traverse_commits():
                    commit_count += 1
                    if commit_count == 1:
                        first_commit_date = commit.author_date.year

                    last_commit_date = commit.author_date.year

                    years_active = last_commit_date - first_commit_date


                # result = f'{line} | {commit_count} commits | {years_active} years active | {first_commit_date}-{last_commit_date}'
                result = f'{years_active},{last_commit_date},{commit_count}'
                print(result)
                output_file.write(f'{result}\n')
                output_file.flush()

            except Exception as e:
                error_message = f"Error processing repository {line}: {e}"
                print(error_message)
                output_file.write(f'{error_message}\n')
                output_file.flush()
                logging.exception(f"Exception encountered while processing {line}")  # Log the exception with traceback
                continue
