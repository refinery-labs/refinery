

def slugify(name):
    return ''.join([
        i for i in name.replace(' ', '-') if i.isalnum() or i == '_'
    ])


def get_unique_workflow_state_name(stage, name, id_):
    return slugify(f"{stage}_{name}_{id_}")


def get_unique_workflow_state_name(stage, name, id_):
    return slugify(f"{stage}_{name}_{id_}")
