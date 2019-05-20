# This builds the .zip file for the Lambda library builder Lambda
# These Lambdas are passed JSON in the following format:
# {
#   "libraries": {
#     "requests": "latest"
#   }
# }
#
# If the libraries already exist in the S3 build bucket
# then that full S3 path is immediately returned (s3://...).
# If it's not in the bucket a .zip file of the npm packages
# is generated and uploaded to the S3 bucket and the path is returned.
#
# The path to the S3 object is a hash with the following input format:
# SHA256( "node8.10--{{KEY_SORTED_LIBRARY_JSON_ARRAY}}" ).zip
#
# For the builder Lambda you MUST set the environment variable BUILD_BUCKET
# to the S3 bucket which is used for package build caching. Note that this
# S3 bucket should be configured to automatically delete objects from the
# cache after >=1 day(s) - this is to allow updates to the packages to make
# it into future builds.
echo "Building Node 8.10 library builder Lambda package..."
rm node8.10-library-builder.zip
rm -rf ./package/runtime/
mkdir ./package/runtime/
cp -r ../../api/custom-runtime/base-src/* ./package/runtime/
cp -r ../../api/custom-runtime/node8.10/runtime ./package/runtime/
cd ./package/
zip -qq -r node8.10-library-builder.zip *
mv node8.10-library-builder.zip ../
cd ../
aws s3 cp node8.10-library-builder.zip s3://refinery-builder-lambdas/
#aws lambda update-function-code --function-name node810-builder-lambda --s3-bucket refinery-builder-lambdas --s3-key node8.10-library-builder.zip
