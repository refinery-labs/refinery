from tasks.build.python import get_python36_base_code, get_python27_base_code
from tasks.build.nodejs import get_nodejs_810_base_code, get_nodejs_10163_base_code, get_nodejs_10201_base_code
from tasks.build.php import get_php_73_base_code
from tasks.build.ruby import get_ruby_264_base_code
from tasks.build.golang import get_go_112_base_code


def get_language_specific_environment_variables(language):
	if language == "python2.7" or language == "python3.6":
		return {
			"PYTHONPATH": "/var/task/",
			"PYTHONUNBUFFERED": "1"
		}
	elif language == "nodejs8.10" or language == "nodejs10.16.3" or language == "nodejs10.20.1":
		return {
			"NODE_PATH": "/var/task/node_modules/"
		}
	return {}


def get_base_lambda_code(app_config, language, code):
	if language == "python3.6":
		return get_python36_base_code(app_config, code)
	elif language == "python2.7":
		return get_python27_base_code(app_config, code)
	elif language == "nodejs8.10":
		return get_nodejs_810_base_code(app_config, code)
	elif language == "nodejs10.16.3":
		return get_nodejs_10163_base_code(app_config, code)
	elif language == "nodejs10.20.1":
		return get_nodejs_10201_base_code(app_config, code)
	elif language == "php7.3":
		return get_php_73_base_code(app_config, code)
	elif language == "ruby2.6.4":
		return get_ruby_264_base_code(app_config, code)
	elif language == "go1.12":
		return get_go_112_base_code(app_config, code)


def get_layers_for_lambda(language):
	"""
	IGNORE THIS NOTICE AT YOUR OWN PERIL. YOU HAVE BEEN WARNED.

	All layers are managed under our root AWS account at 134071937287.

	When a new layer is published the ARNs must be updated in source intentionally
	so that whoever does so must read this notice and understand what MUST
	be done before updating the Refinery customer runtime for customers.

	You must do the following:
	* Extensively test the new custom runtime.
	* Upload the new layer version to the root AWS account.
	* Run the following command on the root account to publicly allow use of the layer:

	aws lambda add-layer-version-permission \
	--layer-name REPLACE_ME_WITH_LAYER_NAME \
	--version-number REPLACE_ME_WITH_LAYER_VERSION \
	--statement-id public \
	--action lambda:GetLayerVersion \
	--principal "*" \
	--region us-west-2

	* Test the layer in a development version of Refinery to ensure it works.
	* Update the source code with the new layer ARN

	Once this is done all future deployments will use the new layers.
	"""
	new_layers = []

	# Add the custom runtime layer in all cases
	if language == "nodejs8.10":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-node810-custom-runtime:30"
		)
	elif language == "nodejs10.16.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs10-custom-runtime:9"
		)
	elif language == "nodejs10.20.1":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-nodejs1020-custom-runtime:1"
		)
	elif language == "php7.3":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-php73-custom-runtime:28"
		)
	elif language == "go1.12":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-go112-custom-runtime:29"
		)
	elif language == "python2.7":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python27-custom-runtime:28"
		)
	elif language == "python3.6":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-python36-custom-runtime:29"
		)
	elif language == "ruby2.6.4":
		new_layers.append(
			"arn:aws:lambda:us-west-2:134071937287:layer:refinery-ruby264-custom-runtime:29"
		)

	return new_layers
