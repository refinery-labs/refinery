from functools import cached_property
from re import compile as regex_compile
#from utils.general import logit


key_identifiers = regex_compile('|'.join([
    'LambdaFunctionQualifiedArn',
    'QueueHandler'
]))


class ServerlessInfoParser:
    def __init__(self, string):
        self.string = string

    @cached_property
    def lambda_resource_map(self):
        result = {}
        parts = self.string.split("Stack Outputs")

        if len(parts) != 2:
            #logit("Unable to split serverless info into parts.", message_type="warning")
            return result

        # Parse dictionary from stack output
        for k, v in (i.strip().split(": ") for i in parts[-1].split("\n") if i):
            if 'LambdaFunctionQualifiedArn' in k:
                h = key_identifiers.sub('', k).lower()

                if len(h) != 32:
                    continue

                result[f'{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'] = v.strip()
            else:
                result[k] = v.strip()
        
        return result
