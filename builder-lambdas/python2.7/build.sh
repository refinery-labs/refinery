# This builds the .zip file for the Lambda library builder Lambda
# These Lambdas are passed JSON in the following format:
# {
#   "libraries": [ "requests", "beautifulsoup4" ]
# }
#
# If the libraries already exist in the S3 build bucket
# then that full S3 path is immediately returned (s3://...).
# If it's not in the bucket a .zip file of the Python packages
# is generated and uploaded to the S3 bucket and the path is returned.
#
# The path to the S3 object is a hash with the following input format:
# SHA256( "python-{{SORTED_LIBRARY_JSON_ARRAY}}" ).zip
#
# For the builder Lambda you MUST set the environment variable BUILD_BUCKET
# to the S3 bucket which is used for package build caching. Note that this
# S3 bucket should be configured to automatically delete objects from the
# cache after >=1 day(s) - this is to allow updates to the packages to make
# it into future builds.
echo "Building Python 2.7 library builder Lambda package..."
rm python-library-builder.zip
cd package/
zip -qq -r python-library-builder.zip *
mv python-library-builder.zip ..
cd ..
aws s3 cp python-library-builder.zip s3://builder-lambda-testing-bucket/
aws lambda update-function-code --function-name python27-builder-lambda --s3-bucket builder-lambda-testing-bucket --s3-key python-library-builder.zip