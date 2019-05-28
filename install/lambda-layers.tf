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