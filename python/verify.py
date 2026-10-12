import os


def verify(path, output_format="md"):
    count = 0
    extension = f".{output_format.casefold().lstrip('.')}"

    if not os.path.isdir(path):
        print(f"Error: Folder does not exist: {path}")
        return 0

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.lower().endswith(extension):
                count += 1

    print(f"Folder: {path}")
    return count
