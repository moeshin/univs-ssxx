import os

script_dir = os.path.abspath(os.path.dirname(__file__))


def get_path(name):
    return os.path.join(script_dir, name)


def read_all(path: str):
    file = open(path)
    data = file.read()
    file.close()
    return data
