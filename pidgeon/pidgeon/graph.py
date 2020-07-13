from pinject import new_object_graph


def get_object_graph():
    return new_object_graph(
        modules=[],
        classes=[],
        binding_specs=[]
    )
