from collections import namedtuple
from pidgeon.framework.component.component import Component
from pidgeon.framework.util.reflect import scan_for_attrs_with_prop


PATH_ATTRIBUTE = "__url_path"


class handle:
    def __init__(self, path):
        self.path = path

    def __call__(self, fn):
        setattr(fn, PATH_ATTRIBUTE, self.path)

        return fn


def get_path_controller_map(controllers, object_graph):
    result = {}

    for controller_cls in controllers:
        controller = object_graph.provide(controller_cls)
        paths_and_fns = scan_for_attrs_with_prop(controller, PATH_ATTRIBUTE)

        for path, fn in paths_and_fns:
            if path in result:
                raise ValueError(f"{path} cannot map to more than one method")

            result[path] = fn

    return result


class Controller(Component):
    pass
