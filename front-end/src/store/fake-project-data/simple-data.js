export default {
  "version": 1,
  "name": "New Project",
  "workflow_states": [
    {
      "layers": [],
      "code": "\ndef main( lambda_input, context ):\n    return False\n",
      "name": "New Lambda",
      "language": "python2.7",
      "libraries": [],
      "memory": 128,
      "type": "lambda",
      "id": "n4f90b532626b416385cca850ac55eb22",
      "max_execution_time": 60
    },
    {
      "api_path": "/",
      "http_method": "GET",
      "type": "api_endpoint",
      "id": "n85304d3c9b3d43e5ab417217b8f762a1",
      "name": "API Endpoint"
    },
    {
      "type": "api_gateway_response",
      "id": "n18e0381e673749cb8da0ec5143274414",
      "name": "API Response"
    }
  ],
  "workflow_relationships": [
    {
      "node": "n85304d3c9b3d43e5ab417217b8f762a1",
      "name": "then",
      "type": "then",
      "next": "n4f90b532626b416385cca850ac55eb22",
      "expression": "",
      "id": "n433d59b1c58a4366ae92949ef1f73d06"
    },
    {
      "node": "n4f90b532626b416385cca850ac55eb22",
      "name": "then",
      "type": "then",
      "next": "n18e0381e673749cb8da0ec5143274414",
      "expression": "",
      "id": "nf45ca04289b34ea6a44c2b5be8f790ad"
    }
  ]
};
