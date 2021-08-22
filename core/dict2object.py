import json


class Object(object):
    def __init__(self, dict_):
        self.__dict__.update(dict_)


def dict2object(dictionary: dict) -> Object:
    return json.loads(json.dumps(dictionary), object_hook=Object)
