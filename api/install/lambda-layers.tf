resource "aws_lambda_layer_version" "refinery-node810-custom-runtime" {
  filename = "node8.10-custom-runtime.zip"
  layer_name = "refinery-node810-custom-runtime"
  description = "Refinery Node 8.10 custom runtime layer."

  compatible_runtimes = ["provided"]
}

resource "aws_lambda_layer_version" "refinery-php73-custom-runtime" {
  filename = "php7.3-custom-runtime.zip"
  layer_name = "refinery-php73-custom-runtime"
  description = "Refinery PHP 7.3 custom runtime layer."

  compatible_runtimes = ["provided"]
}

resource "aws_lambda_layer_version" "refinery-go112-custom-runtime" {
  filename = "go1.12-custom-runtime.zip"
  layer_name = "refinery-go112-custom-runtime"
  description = "Refinery go 1.12 custom runtime layer."

  compatible_runtimes = ["provided"]
}

resource "aws_lambda_layer_version" "refinery-python27-custom-runtime" {
  filename = "python2.7-custom-runtime.zip"
  layer_name = "refinery-python27-custom-runtime"
  description = "Refinery Python 2.7 custom runtime layer."

  compatible_runtimes = ["provided"]
}