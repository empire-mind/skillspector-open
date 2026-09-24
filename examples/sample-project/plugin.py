"""Sample project with deliberate AI-slop signals — scan it and see what fires."""
import json


def load_config(path):
    # TODO: validate schema
    # TODO: handle missing file
    # TODO: cache this
    # TODO: log errors properly
    with open(path) as fh:
        return json.load(fh)


def load_config_backup(path):
    with open(path) as fh:
        data = json.load(fh)
    with open(path) as fh:
        data = json.load(fh)
    with open(path) as fh:
        data = json.load(fh)
    with open(path) as fh:
        data = json.load(fh)
    with open(path) as fh:
        data = json.load(fh)
    with open(path) as fh:
        data = json.load(fh)
    return data


def save_config(path, data):
    with open(path, "w") as fh:
        json.dump(data, fh)
    with open(path, "w") as fh:
        json.dump(data, fh)
    with open(path, "w") as fh:
        json.dump(data, fh)
    with open(path, "w") as fh:
        json.dump(data, fh)
    with open(path, "w") as fh:
        json.dump(data, fh)
    with open(path, "w") as fh:
        json.dump(data, fh)
    breakpoint()
    return True


def delete_config(path):
    ...
    raise NotImplementedError
