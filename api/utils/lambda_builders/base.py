import uuid
from abc import ABCMeta, abstractmethod
import io
import zipfile

import yaml

from utils.aws_client import get_aws_client
from utils.lambda_builders.build_config import BuildConfig
from utils.zip import EMPTY_ZIP_DATA, write_file_to_zip


# TODO: Instrument this class with logging


class BaseLambdaBuilder:
	__metaclass__ = ABCMeta

	imageOverride = None

	def __init__( self, credentials, build_config ):
		# type: (dict[str, str], BuildConfig) -> None

		self.credentials = credentials

		self.build_config = build_config

		self.codebuild_client = get_aws_client(
			"codebuild",
			credentials
		)

		self.s3_client = get_aws_client(
			"s3",
			credentials
		)

		from server import TaskSpawner
		self.task_spawner = TaskSpawner

	def random_uuid( self ):
		return str( uuid.uuid4() )

	def create_lambda_zip( self ):

		# Create empty zip file
		codebuild_zip = io.BytesIO( EMPTY_ZIP_DATA )

		with zipfile.ZipFile( codebuild_zip, "a", zipfile.ZIP_DEFLATED ) as zip_file_handler:
			self.build_base_zip( zip_file_handler )

		codebuild_zip_data = codebuild_zip.getvalue()
		codebuild_zip.close()

		return codebuild_zip_data

	def run_codebuild( self ):

		codebuild_zip_data = self.create_lambda_zip()

		# S3 object key of the build package, randomly generated.
		s3_key = "buildspecs/" + self.random_uuid() + ".zip"

		# Write the CodeBuild build package to S3
		# TODO: Log this response
		s3_response = self.s3_client.put_object(
			Bucket=self.credentials[ "lambda_packages_bucket" ],
			Body=codebuild_zip_data,
			Key=s3_key,
			# THIS HAS TO BE PUBLIC READ FOR SOME FUCKED UP REASON I DONT KNOW WHY
			ACL="public-read",
		)

		extra_codebuild_args = {}

		if self.imageOverride:
			extra_codebuild_args["imageOverride"] = self.imageOverride

		# Fire-off the build
		codebuild_response = self.codebuild_client.start_build(
			projectName="refinery-builds",
			sourceTypeOverride="S3",
			sourceLocationOverride=self.credentials[ "lambda_packages_bucket" ] + "/" + s3_key,
			**extra_codebuild_args
		)

		build_id = codebuild_response[ "build" ][ "id" ]

		return build_id

	def build_base_zip( self, zip_file_handler ):

		# Write buildspec.yml defining the build process
		write_file_to_zip(
			zip_file_handler,
			self.build_config.buildspec_filename,
			yaml.dump(
				self.build_config.buildspec_template
			)
		)

		# Write the code file
		write_file_to_zip(
			zip_file_handler,
			self.build_config.code_filename,
			str( self.build_config.code )
		)

		self.additional_base_zip_build_steps( zip_file_handler )

	# Optional extra steps for adding to the zip
	@abstractmethod
	def additional_base_zip_build_steps( self, zip_file_handler ):
		pass

	def get_s3_zip_path( self ):
		return self.task_spawner._get_final_zip_package_path(
			self.build_config.language,
			self.build_config.libraries_object
		)

	def check_for_cached_build( self ):
		final_s3_package_zip_path = self.get_s3_zip_path()

		print("get_s3_zip_path", final_s3_package_zip_path)

		cached_build = self.task_spawner._s3_object_exists(
			self.credentials,
			self.credentials[ "lambda_packages_bucket" ],
			final_s3_package_zip_path
		)

		if cached_build:
			return self.task_spawner._read_from_s3(
				self.credentials,
				self.credentials[ "lambda_packages_bucket" ],
				final_s3_package_zip_path
			)

		return None

	def get_built_lambda_package_zip( self ):
		cached_zip = self.check_for_cached_build()

		# Safely skip building again if we located a previously built package
		if cached_zip:
			return cached_zip

		# Kick off CodeBuild
		build_id = self.run_codebuild()

		# This continually polls for the CodeBuild build to finish
		# Once it does it returns the raw artifact zip data.
		return self.task_spawner._get_codebuild_artifact_zip_data(
			self.credentials,
			build_id,
			self.get_s3_zip_path()
		)

