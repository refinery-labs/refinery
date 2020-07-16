from os import listdir
from os.path import join
from importlib import import_module


def get_impls(cls, module_base, project_root):
    classes = []
    path = join(project_root, *module_base.split('.'))
    files = [
        i.replace(".py", "") for i in listdir(path)
        if i != "__init__.py"
        and i.endswith('.py')
    ]

    for file_name in files:
        module = get_module(module_base, file_name)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if not isinstance(attr, type) or attr == cls:
                continue

            if issubclass(attr, cls):
                classes.append(attr)

    return classes


def get_module(base, name):
    try:
        return import_module(".{}".format(name), package="{}".format(base))
    except SystemError:
        return import_module("{}.{}".format(base, name))


def scan_for_attrs_with_prop(obj, prop):
    result = []

    for attr_name in dir(obj):
        attr = getattr(obj, attr_name)
        prop_val = getattr(attr, prop, None)

        if prop_val is not None:
            result.append((prop_val, attr))

    return result
