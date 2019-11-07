import six

from utils.lambda_builders.base import BaseLambdaBuilder
from utils.lambda_builders.build_config import BuildConfig
from utils.zip import write_file_to_zip

# These commands will be run for both editor and production lambda builds
base_build_commands = [
	"export GOPATH=\"$(pwd)/go\"",
	"export GOBIN=$GOPATH/bin",
	# In the future, if we want to parse the source code in a Lambda for dependencies, use this:
	# go list -f '{{ join .Deps \"\n\" }}'
	"go mod download"
]

# Specific commands for production lambda builds
production_build_commands = [
	# Parses the source code and installs any dependencies referenced there
	"go get",
	# Outputs a binary for fast execution in production
	"go build lambda.go"
]

# Used when creating the zip for the Lambda
empty_folders = [
	"bin",
	"pkg",
	"src"
]


class GoBuildConfig(BuildConfig):

	def __init__( self, language, code, libraries, build_mode, lambda_base_codes ):

		BuildConfig.__init__( self, language, code, "lambda.go", libraries, build_mode, lambda_base_codes )

		self.go_mod_file = self.generate_go_mod_file()

	# Generates a go.mod file for the given libraries
	def get_go_mod_statements( self, libraries ):
		commands = [
			"module refinery.io/build/output"
		]

		for library in libraries:
			# Only add valid libraries
			if library is None or not isinstance( library, six.string_types ):
				continue

			# Syntax for requiring a module in the go.mod file
			commands.append( "require " + library.rstrip() + " latest" )

		return commands

	def get_codebuild_commands( self, build_mode ):
		# Production step runs a build step before continuing
		if build_mode is "production":
			return base_build_commands + production_build_commands

		return base_build_commands

	def generate_go_mod_file( self ):
		return "\n".join( self.get_go_mod_statements( self.libraries ) )

	def create_codebuild_template( self ):

		commands = self.get_codebuild_commands(self.build_mode)

		return {
			"artifacts": {
				"files": [
					"**/*"
				]
			},
			"phases": {
				"build": {
					"commands": commands
				},
				"install": {
					"runtime-versions": {
						"golang": 1.12
					}
				}
			},
			"run-as": "root",
			"version": 0.2
		}


class GoLambdaBuilder(BaseLambdaBuilder):

	def __init__( self, credentials, build_config ):
		BaseLambdaBuilder.__init__( self, credentials, build_config )

	def additional_base_zip_build_steps( self, zip_file_handler ):

		# Write the go.mod file with dependencies
		write_file_to_zip(
			zip_file_handler,
			"go.mod",
			str( self.build_config.go_mod_file )
		)

		# Create empty folders for bin, pkg, and src
		for empty_folder in empty_folders:
			write_file_to_zip(
				zip_file_handler,
				"go/" + empty_folder + "/blank",
				""
			)

