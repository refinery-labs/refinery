from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


LAMBDA_FUNCTION_TEMPLATE = """
def lambda_handler(event, context):
    return_data = event['return_data']
    node_id = event['node_id']
    result = perform(node_id, return_data)

    return json.dumps(result)


def perform(node_id, return_data):
    {expressions}
    raise ValueError('Invalid node uuid')


{transition_functions}
"""


TRANSITION_FUNCTION_TEMPLATE = """
def {fn_name}(return_data):
    return {expression}
"""


BOOL_EXPR_TEMPLATE = """
    {statement} node_id == '{node_id}':
        return {fn_name}(return_data)
"""


class IfTransitionBuilder:
    def __init__(self, deploy_config):
        self.deploy_config = deploy_config
        self.if_transitions = self.get_if_transitions()

    def get_if_transitions(self):
        relationships = self.deploy_config.get("workflow_relationships", [])
        result = []

        for relationship in relationships:
            transition_type = relationship.get('type')
            expression = relationship.get('expression')
            node = relationship.get('node')

            if transition_type == 'if' and expression and node:
                result.append(relationship)

        return result

    def build(self):
        if not self.if_transitions:
            return

        package_zip = BytesIO()

        with ZipFile(package_zip, "a", ZIP_DEFLATED) as zip_file_handler:
            for transition in self.if_transitions:
                self.add_transition(package_zip, transition)

        zip_data = package_zip.getvalue()
        package_zip.close()

        return zip_data

    @property
    def lambda_function(self):
        expressions = '\n'.join([
            self.get_bool_expr(i, j)
            for i, j in enumerate(self.if_transitions)
        ])
        transition_functions = '\n'.join([
            self.get_transition_fn(i)
            for i in self.if_transitions
        ])

        return LAMBDA_FUNCTION_TEMPLATE.format(
            expressions=expressions,
            transition_functions=transition_functions
        )

    def get_fn_name(self, node_id):
        return "perform_{}".format(node_id.replace('-', '_'))

    def get_transition_fn(self, transition):
        fn_name = self.get_fn_name(transition['node'])
        expression = transition['expression']
 
        return TRANSITION_FUNCTION_TEMPLATE.format(
            fn_name=fn_name,
            expression=expression
        )

    def get_bool_expr(self, index, transition):
        node_id = transition['node']
        fn_name = self.get_fn_name(node_id)
        statement = 'if' if index == 0 else 'elif'

        return BOOL_EXPR_TEMPLATE.format(
            statement=statement,
            node_id=node_id,
            fn_name=fn_name
        )
