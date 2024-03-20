import unittest
from unittest.mock import patch, mock_open
from pathlib import Path
from utility import util, config


class MyModuleTests(unittest.TestCase):

    @patch('os.walk')
    def test_get_python_files_from_directory(self, mock_walk):
        mock_walk.return_value = [
            ('/path/to/dir', ('subdir',), ('file.py', 'not_a_python_file.txt')),
        ]
        expected_files = [str(Path('/path/to/dir/file.py').resolve())]
        directory = Path('/path/to/dir').resolve()
        result = util.get_python_files_from_directory(directory)
        normalized_result = [str(Path(file).resolve()) for file in result]
        self.assertEqual(expected_files, normalized_result)

    def test_get_repo_name_from_url(self):
        test_cases = [
            ("https://github.com/user/repo_name.git", "repo_name"),
            ("https://github.com/user/repo_name/", "repo_name"),
            ("https://github.com/user/repo_name", "repo_name")
        ]
        for repo_url, expected in test_cases:
            result = util.get_repo_name_from_url_or_path(repo_url)
            self.assertEqual(result, expected)

    def test_get_repo_owner_from_url(self):
        """ Test  """
        repo_url = "https://github.com/owner_name/repo_name"
        expected_owner = "owner_name"
        result = util.get_repo_owner_from_url(repo_url)
        self.assertEqual(result, expected_owner)

    def test_get_repo_name_from_path(self):
        """ Test that we can get a repository name from a path """
        test_cases = [
            ("C:\\path\\to\\repo_name", "repo_name"),
            ("/path/to/repo_name/", "repo_name"),
            ("/path/to/repo_name", "repo_name")
        ]
        for path, expected in test_cases:
            result = util.get_repo_name_from_url_or_path(path)
            self.assertEqual(result, expected)

    @patch('builtins.open', new_callable=mock_open,
           read_data="https://github.com/user/repo1\nhttps://github.com/user/repo2")
    def test_get_repository_urls_from_file(self, mock_file):
        """ Test to make sure that it extracts urls from a file """
        file_path = Path(config.REPOSITORY_URLS)
        expected_urls = ["https://github.com/user/repo1", "https://github.com/user/repo2"]
        result = util.get_repository_urls_from_file(file_path)
        self.assertEqual(result, expected_urls)
        mock_file.assert_called_once_with(config.REPOSITORY_URLS, 'r')

    @patch('utility.config.REPOSITORIES_FOLDER', new_callable=lambda: Path('/base/repo'))
    def test_get_file_relative_path_from_absolute_path(self, mock_base_path):
        """ Tests that the function returns a relative path, based on the absolute path provided by config.py """
        absolute_path = f'{config.REPOSITORIES_FOLDER}/subfolder/file.py'
        expected_relative_path = 'subfolder/file.py'
        actual_relative_path = util.get_file_relative_path_from_absolute_path(absolute_path)
        self.assertEqual(expected_relative_path, actual_relative_path)

    @patch('utility.config.REPOSITORIES_FOLDER', Path('/base/repo/'))
    def test_get_path_to_repo(self):
        """ Test that we can get the path to a repository form an url """
        repo_url = 'https://github.com/user/repo_name'
        expected_path = Path('/base/repo/repo_name')
        actual_path = util.get_path_to_repo(repo_url)
        self.assertEqual(expected_path, actual_path)

    def test_sanitize_url(self):
        """ See if we can sanitize the url """
        test_cases = [
            ("https://github.com/user/repo_name.git/", "https://github.com/user/repo_name.git"),
            ("  https://github.com/user/repo_name  ", "https://github.com/user/repo_name"),
            ("\nhttps://github.com/user/repo_name\n", "https://github.com/user/repo_name"),
        ]
        for input_url, expected_url in test_cases:
            sanitized_url = util.sanitize_url(input_url)
            self.assertEqual(expected_url, sanitized_url)

    def test_format_size(self):
        """See if it provides the correct format, only used in logging, not really needed"""
        test_cases = [
            (512, "512 KB"),
            (2048, "2.00 MB"),
            (3 * 1024 * 1024, "3.00 GB"),
        ]
        for size_in_kb, expected_output in test_cases:
            formatted_size = util.kb_to_mb_gb(size_in_kb)
            self.assertEqual(expected_output, formatted_size)


if __name__ == '__main__':
    unittest.main()

