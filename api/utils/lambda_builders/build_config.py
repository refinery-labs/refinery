from abc import ABCMeta, abstractmethod


class BuildConfig:
	__metaclass__ = ABCMeta

	buildspec_filename = 'buildspec.yml'

	def __init__( self, language, code, code_filename, libraries, build_mode, lambda_base_codes ):
		# type: (str, str, str, List, str, Dict[str, str]) -> None
		self.language = language

		# Make a copy of the original code before we attach the template to it
		self.original_code = code

		# Attach the Refinery code to imported code.
		self.code = code + "\n\n" + lambda_base_codes[language]

		self.code_filename = code_filename

		self.libraries = libraries
		self.build_mode = build_mode

		self.buildspec_template = self.create_codebuild_template()

		self.libraries_object = self.create_libraries_object( libraries )

	def create_libraries_object( self, libraries ):

		libraries_object = {}
		for library in libraries:
			libraries_object[ str( library ) ] = "latest"

		return libraries_object

	@abstractmethod
	def create_codebuild_template( self ):
		pass


