class TornadoWebsocketInjectionMixin:
    dependencies = None

    @staticmethod
    def set_object_deps(object_graph, obj, dep_class):
        provided_deps = object_graph.provide(dep_class)
        for name, dep in provided_deps.__dict__.items():
            setattr(obj, name, dep)

    def initialize(self, **kwargs):
        object_graph = kwargs["object_graph"]

        self.set_object_deps(object_graph, self, self.dependencies)
