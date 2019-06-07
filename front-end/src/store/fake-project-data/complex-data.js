export default {
  version: 1,
  name: 'Many Blocks Example',
  workflow_states: [
    {
      layers: [],
      code:
        '\ndef main( lambda_input, context ):\n    print( "Trigger by API endpoint" )\n    print( lambda_input )\n    return "Done"\n',
      name: 'Final',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n0147e8270ec7429e9258dd7eca5ff474',
      max_execution_time: 60
    },
    {
      description: 'Example scheduled rule description.',
      input_string: '',
      schedule_expression: 'rate(1 hour)',
      type: 'schedule_trigger',
      id: 'n4201e0162e6a4f1897dd750271c9a73a',
      name: 'Bad Timer'
    },
    {
      type: 'sns_topic',
      id: 'n0ae3b1fbfee84d2791747148e28235b3',
      name: 'Debug Topic'
    },
    {
      name: 'Debug Queue',
      batch_size: 1,
      type: 'sqs_queue',
      id: 'nf3929bb9d27a49e09bcc93c372cf9be9'
    },
    {
      api_path: '/',
      http_method: 'GET',
      type: 'api_endpoint',
      id: 'n3116d00a0dd943bcae22ddc0487da82d',
      name: 'API Endpoint'
    },
    {
      type: 'api_gateway_response',
      id: 'n5545badbbf8c43f5a944d719c87cf6fb',
      name: 'API Response'
    },
    {
      layers: [],
      code:
        '\ndef main( lambda_input, context ):\n    print( "Trigger by time trigger: " )\n    print( lambda_input )\n    return False\n',
      name: 'Timer Target',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n864b7144e0ce4dbe8f382952297fcdc0',
      max_execution_time: 60
    },
    {
      layers: [],
      code:
        '\ndef main( lambda_input, context ):\n    print( "Trigger by SNS topic trigger: " )\n    print( lambda_input )\n    return False\n',
      name: 'SNS Target',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'nf37908b8d5ae4ea682adad96f98b9225',
      max_execution_time: 60
    },
    {
      layers: [],
      code:
        '\ndef main( lambda_input, context ):\n    print( "Trigger by SQS trigger: " )\n    print( lambda_input )\n    return "wew"\n',
      name: 'SQS Target',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n6df2d783f3a748f4bd7eeb60c145c23c',
      max_execution_time: 60
    },
    {
      type: 'sns_topic',
      id: 'nd64e36910ccf4ecfb57b1075d305a1ba',
      name: 'Debug Output'
    },
    {
      layers: [],
      code:
        '\ndef main( lambda_input, context ):\n    print( "Triggered by SNS topic triggered by Lambda: " )\n    print( lambda_input )\n    return False\n',
      name: 'SNS Output',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n187078b30fa2407fa1e65606b06d46e5',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return True\n',
      name: 'start',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n36be2f21b71b4d30a851f8616866ec33',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return "test"\n',
      name: 'return "test"',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n31d4b43425374c0cb0c58348715f088a',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return False\n',
      name: 'if PASS',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'nd98735e3fcb4423081b7255122c257b3',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return False\n',
      name: 'if FAIL',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n659cb49307f44e289af4fe829faae670',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    1/0\n    return False\n',
      name: 'throw exception',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n6fddaa73ca314d4d8111091ce4fc657c',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return False\n',
      name: 'exception PASS',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'ncb4e183604794453a364f094507d437f',
      max_execution_time: 60
    },
    {
      layers: [],
      code: '\ndef main( lambda_input, context ):\n    return False\n',
      name: 'exception FAIL',
      language: 'python2.7',
      libraries: [],
      memory: 128,
      type: 'lambda',
      id: 'n339a93ef871a40c3b9765f1270207fd4',
      max_execution_time: 60
    }
  ],
  workflow_relationships: [
    {
      node: 'n3116d00a0dd943bcae22ddc0487da82d',
      name: 'then',
      type: 'then',
      next: 'n0147e8270ec7429e9258dd7eca5ff474',
      expression: '',
      id: 'n2144d52270714438805b73402b1ebeca'
    },
    {
      node: 'n0147e8270ec7429e9258dd7eca5ff474',
      name: 'then',
      type: 'then',
      next: 'n5545badbbf8c43f5a944d719c87cf6fb',
      expression: '',
      id: 'n7412dbbcc02b4c64afc94ec0386a3ec6'
    },
    {
      node: 'n4201e0162e6a4f1897dd750271c9a73a',
      name: 'then',
      type: 'then',
      next: 'n864b7144e0ce4dbe8f382952297fcdc0',
      expression: '',
      id: 'n45835fe495c345ed89eae07b3a23eb09'
    },
    {
      node: 'n0ae3b1fbfee84d2791747148e28235b3',
      name: 'then',
      type: 'then',
      next: 'nf37908b8d5ae4ea682adad96f98b9225',
      expression: '',
      id: 'n2b67d039eafe4288afaa75837d856b53'
    },
    {
      node: 'nf3929bb9d27a49e09bcc93c372cf9be9',
      name: 'then',
      type: 'then',
      next: 'n6df2d783f3a748f4bd7eeb60c145c23c',
      expression: '',
      id: 'n50b1e984146a416a953d2a8996d1362f'
    },
    {
      node: 'n6df2d783f3a748f4bd7eeb60c145c23c',
      name: 'then',
      type: 'then',
      next: 'nd64e36910ccf4ecfb57b1075d305a1ba',
      expression: '',
      id: 'nddf364b427c743fab6ae871b5b6c1361'
    },
    {
      node: 'nd64e36910ccf4ecfb57b1075d305a1ba',
      name: 'then',
      type: 'then',
      next: 'n187078b30fa2407fa1e65606b06d46e5',
      expression: '',
      id: 'n54d5da4d4d1d43959668f2e1befa0c54'
    },
    {
      node: 'n36be2f21b71b4d30a851f8616866ec33',
      name: 'then',
      type: 'then',
      next: 'n31d4b43425374c0cb0c58348715f088a',
      expression: '',
      id: 'ne9a6b56dfcf7471baddeb2b4acde9dec'
    },
    {
      node: 'n31d4b43425374c0cb0c58348715f088a',
      name: 'if "test"',
      type: 'if',
      next: 'nd98735e3fcb4423081b7255122c257b3',
      expression: 'return_data == "test"',
      id: 'n40a8c34495684d7bbcf58a71b10a6008'
    },
    {
      node: 'n31d4b43425374c0cb0c58348715f088a',
      name: 'if "pew"',
      type: 'if',
      next: 'n659cb49307f44e289af4fe829faae670',
      expression: 'return_data == "pew"',
      id: 'n4bbe5846ae1d4ffb83a5e7c1047dece0'
    },
    {
      node: 'n36be2f21b71b4d30a851f8616866ec33',
      name: 'then',
      type: 'then',
      next: 'n6fddaa73ca314d4d8111091ce4fc657c',
      expression: '',
      id: 'na87ebd38f9db4cb99b85d2610a8eb332'
    },
    {
      node: 'n6fddaa73ca314d4d8111091ce4fc657c',
      name: 'exception',
      type: 'exception',
      next: 'ncb4e183604794453a364f094507d437f',
      expression: '',
      id: 'n0577914620b74ed6b2ab5c89af39a87b'
    },
    {
      node: 'n6fddaa73ca314d4d8111091ce4fc657c',
      name: 'then',
      type: 'then',
      next: 'n339a93ef871a40c3b9765f1270207fd4',
      expression: '',
      id: 'na57bd4e3125246838862369eb8ece0fd'
    },
    {
      node: 'n6fddaa73ca314d4d8111091ce4fc657c',
      name: 'else',
      type: 'else',
      next: 'n339a93ef871a40c3b9765f1270207fd4',
      expression: '',
      id: 'ne4294e303bb94698a3bef06ea7831d17'
    },
    {
      node: 'n6fddaa73ca314d4d8111091ce4fc657c',
      name: 'if true',
      type: 'if',
      next: 'n339a93ef871a40c3b9765f1270207fd4',
      expression: 'True',
      id: 'n359d3de55ade4867b379318f5df13db4'
    },
    {
      node: 'n31d4b43425374c0cb0c58348715f088a',
      name: 'exception',
      type: 'exception',
      next: 'n659cb49307f44e289af4fe829faae670',
      expression: '',
      id: 'n47277c91ef0a4a1ea73c55a81f60256a'
    },
    {
      node: 'n31d4b43425374c0cb0c58348715f088a',
      name: 'else',
      type: 'else',
      next: 'n659cb49307f44e289af4fe829faae670',
      expression: '',
      id: 'n7b651f966354462eaf911ad5cc61293c'
    },
    {
      node: 'n31d4b43425374c0cb0c58348715f088a',
      name: 'then',
      type: 'then',
      next: 'nd98735e3fcb4423081b7255122c257b3',
      expression: '',
      id: 'n9fff0a0122024bdb928ef33f44f2b9da'
    }
  ]
};
