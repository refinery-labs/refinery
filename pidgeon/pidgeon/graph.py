from pidgeon.framework.constants import PROJECT_ROOT
from pidgeon.framework.component.controller import Controller
from pidgeon.framework.component.gateway import Gateway
from pidgeon.framework.component.service import Service
from pidgeon.framework.util.reflect import get_impls
from pinject import new_object_graph, BindingSpec


services = get_impls(Service, "pidgeon.service", PROJECT_ROOT)
gateways = get_impls(Gateway, "pidgeon.gateway", PROJECT_ROOT)
controllers = get_impls(Controller, "pidgeon.controller", PROJECT_ROOT)
binding_specs = [
    B() for B in
    get_impls(BindingSpec, "pidgeon.framework.binding", PROJECT_ROOT)
]
dep_classes = services + gateways


def get_object_graph():
    return new_object_graph(
        modules=[],
        classes=dep_classes,
        binding_specs=binding_specs
    )
