import json
import os

import pytest
import yaml
import six
from hypothesis import given
from hypothesis.strategies import dictionaries, text, one_of, lists, integers, deferred

from config.app_config import AppConfig


@pytest.fixture()
def config_folder( tmpdir_factory ):
	return tmpdir_factory.mktemp( "config" )


def generate_child_dictionary():
	return dictionaries(
		text( max_size=20 ),
		one_of(
			lists(
				integers( max_value=10 ),
				max_size=4
			),
			dictionaries(
				text( max_size=20 ),
				lists(
					text( max_size=20 ),
					max_size=4
				),
				max_size=4
			),
			text( max_size=20 ),
			integers( max_value=10 )
		),
		max_size=4
	)


def generate_config_value():
	return one_of(
		text( max_size=20 ),
		lists( integers( max_value=10 ), max_size=3 ),
		generate_child_dictionary()
	)


def generate_fake_config():
	return dictionaries(
		text( max_size=20 ),
		generate_config_value(),
		max_size=4
	)


def assert_merged_lists_merge_properly( l1, l2, merged_list ):

	assert isinstance( merged_list, list ), "Output is a list"

	assert len( merged_list ) == ( len( l1 ) + len( l2 ) )

	for i in l1:
		assert i in merged_list, "Output list contains values from first list"

	for i in l2:
		assert i in merged_list, "Output list contains values from second list"


def assert_merged_dicts_merge_properly( d1, d2, merged_dict ):

	assert isinstance( merged_dict, dict ), "Output is a dict"

	for key, value in six.viewitems( d1 ):
		assert key in merged_dict, "Output dict contains key from first list"

	for key, value in six.viewitems( d2 ):
		assert key in merged_dict, "Output dict contains key from second list"

		# Test for keys in both dicts
		if key in d1:
			if type( d1[ key ] ) is not type( d2[ key ] ):
				assert json.dumps( merged_dict[ key ], sort_keys=True ) == json.dumps( d2[ key ], sort_keys=True ), \
					"Output dict prefers value from second dict"

			if isinstance( d1[ key ], list ) and isinstance( d2[ key ], list ):
				assert_merged_lists_merge_properly( d1[ key ], d2[ key ], merged_dict[ key ] )

			if isinstance( d1[ key ], dict ) and isinstance( d2[ key ], dict ):
				assert_merged_dicts_merge_properly( d1[ key ], d2[ key ], merged_dict[ key ] )


@given( deferred( generate_fake_config ), deferred( generate_fake_config ) )
def test_merging_configs( config_folder, a, b ):

	def make_config_contents( contents ):
		return dict(
			config=contents
		)

	config_folder.join( "common.yaml" ).write( yaml.safe_dump( make_config_contents( a ) ) )
	config_folder.join( "test.yaml" ).write( yaml.safe_dump( make_config_contents( b ) ) )

	# Test merging 2 dicts
	app_config_instance = AppConfig( "test", config_folder, set_env_vars=False )

	config = app_config_instance._config

	assert isinstance( config, dict ), "Output from merging is a dict"

	for key, value in six.viewitems( a ):
		assert key in config, "Output config has expected key from first config"

	for key, value in six.viewitems( b ):
		assert key in config, "Output config has expected key from second config"

	overrides = dict(
		foobar="woot",
		foobaz="yeee"
	)

	# Test merging with overrides
	app_config_instance = AppConfig( "test", config_folder, set_env_vars=False, overrides=overrides )

	config = app_config_instance._config

	assert isinstance( config, dict ), "Output from merging is a dict"

	for key, value in six.viewitems( a ):
		assert key in config, "Output config has expected key from first config"

	for key, value in six.viewitems( b ):
		assert key in config, "Output config has expected key from second config"

	for key, value in six.viewitems( overrides ):
		assert key in config, "Output config has expected key from overrides"


@given( lists( deferred( generate_config_value ) ), lists( deferred( generate_config_value ) ) )
def test_merging_two_lists( l1, l2 ):
	a = dict(
		test_list=l1
	)
	b = dict(
		test_list=l2
	)

	merged_list = AppConfig._merge_key( a, b, "test_list" )

	assert_merged_lists_merge_properly( l1, l2, merged_list )


@given( deferred( generate_child_dictionary ), deferred( generate_child_dictionary ) )
def test_merging_two_dicts( d1, d2 ):
	a = dict(
		test_dict=d1
	)
	b = dict(
		test_dict=d2
	)

	merged_dict = AppConfig._merge_key( a, b, "test_dict" )

	assert_merged_dicts_merge_properly( d1, d2, merged_dict )


def test_setting_and_reading_env_var():

	# Set at least one variable (doesn't work every platform though)
	os.environ[ "SOME_RANDOM_ENV_VAR" ] = "foobar"

	# Create dict with environment variables in it
	env_var_dict = AppConfig._get_env_vars_dict()

	assert "env" in env_var_dict, "Output variable nests environment variables under 'env'"

	# Check every environment variable is read correctly.
	# Note: Mostly doing this because we can't reliably set env vars ourselves.
	for key, value in six.viewitems( dict( os.environ ) ):
		assert key in env_var_dict[ "env" ], "Environment variable exists in output dict"
		assert env_var_dict[ "env" ][ key ] == os.environ[ key ], "Environment variable values match"

