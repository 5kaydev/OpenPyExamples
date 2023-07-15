from pathlib import Path


def delete_file(file_path: str) -> None:
    """
    Delete a file.
    :param file_path: The file path
    """
    Path(file_path).unlink(True)


def move_file(source: str, target: str) -> None:
    """
    Move the source file to target.
    :param source: The source file path
    :param target: The target file path
    """
    target_path = Path(target)
    target_path.unlink(True)
    Path(source).rename(target_path)


def save_file(file_path: str, content: str) -> None:
    """
    Save the given content in a text file at the given path.
    :param file_path: The file path
    :param content: The file content.
    """
    with open(file_path, "w", encoding='UTF-8') as feature_file:
        print(content, file=feature_file)


def scan_dir(path: str, pattern: str) -> [Path]:
    """
    Gets the list of files matching the given pattern in the given directory
    :param path: The directory to scan
    :param pattern: The file extension
    :return: The list of files matching the given pattern in the given directory
    """
    return [path for path in Path(path).glob(pattern)]


def wipe_dir(path: str, pattern: str) -> None:
    """
    Deletes the files matching the given pattern in the given directory
    :param path: The directory to scan
    :param pattern: The file extension
    """
    for path in scan_dir(path, pattern):
        path.unlink()
