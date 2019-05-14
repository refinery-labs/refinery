function handler () {
  export NPM_PATH="$LAMBDA_TASK_ROOT/bin/:$PATH"
  export PATH="$LAMBDA_TASK_ROOT/bin/:$PATH"
  export PATH="$LAMBDA_TASK_ROOT/lib/node_modules/npm/bin/:$PATH"
  export NODE_PATH="$LAMBDA_TASK_ROOT"
  export LD_LIBRARY_PATH="$(pwd)/bin/"
  export PYTHONPATH="$LAMBDA_TASK_ROOT/lib/python2.7/site-packages/"
  
  export BUILD_DIRECTORY="/tmp/build/"
  
  # Clear out previous build directory
  rm -rf $BUILD_DIRECTORY
  
  # Create new build directory
  mkdir $BUILD_DIRECTORY
  
  # Copy runtime to the build directory
  cp -r $LAMBDA_TASK_ROOT/runtime/* $BUILD_DIRECTORY
  
  # Get a JSON sorted and minified version of the libraries
  # so we can use it for a key for the hash function
  export LIBRARIES_JSON=$(echo -n "$1" | jq -c --sort-keys .libraries)
  
  echo "Libraries hash input: " 1>&2;
  echo $LIBRARIES_JSON 1>&2;
  
  # Creates a hash for S3 which we can use to immediately return
  # already generated library packages.
  LIBRARIES_HASH=$(echo -n "node8.10-$LIBRARIES_JSON" | sha256sum | awk -F" " '{print $1}' )

  # Generate S3 object path
  S3_OBJECT_PATH="$LIBRARIES_HASH.zip"
  
  # Generate S3 full path
  PACKAGE_S3_PATH="s3://$BUILD_BUCKET/$S3_OBJECT_PATH"
  
  # TODO: Write code to immediately return the same S3 path if it already exists.
  OBJECT_CHECK_OUTPUT=$(python "$LAMBDA_TASK_ROOT/lib/python2.7/site-packages/awscli/__main__.py" s3api head-object --bucket $BUILD_BUCKET --key $S3_OBJECT_PATH 2>&1 || true)
  
  # Substring determining if the object doesn't exist
  NOT_FOUND_STRING="An error occurred (404)"
  
  # Check to see if the object exists, if it does just immediately
  # return the full S3 path to the object in the cache.
  if [[ "$OBJECT_CHECK_OUTPUT" != *"$NOT_FOUND_STRING"* ]]; then
	echo "Object exists in cache already! Returning S3 path..." 1>&2;
    echo "$PACKAGE_S3_PATH"
    exit 0
  fi
  
  echo "No previous build in cache, building dependencies..." 1>&2;
  
  cd $BUILD_DIRECTORY
  
  # Build package.json
  echo "Writing new package.json!" 1>&2;
  jq '.dependencies=(env.LIBRARIES_JSON|fromjson)' $LAMBDA_TASK_ROOT/package.json.template > $BUILD_DIRECTORY/package.json

  echo "Package JSON: " 1>&2;
  cat $BUILD_DIRECTORY/package.json 1>&2;
  
  export HOME=$BUILD_DIRECTORY
  
  NPM_INSTALL_COMMAND="node $LAMBDA_TASK_ROOT/bin/npm-cli.js --prefix $BUILD_DIRECTORY --no-update-notifier install"

  echo "NPM install command: " 1>&2;
  echo "$NPM_INSTALL_COMMAND" 1>&2;
  $NPM_INSTALL_COMMAND 1>&2;
  
  zip -qq -r libraries.zip * 1>&2;
  
  python "$LAMBDA_TASK_ROOT/lib/python2.7/site-packages/awscli/__main__.py" s3 cp /tmp/build/libraries.zip "$PACKAGE_S3_PATH" 1>&2;
  
  RESPONSE="Echoing request: '$EVENT_DATA'"

  echo $PACKAGE_S3_PATH
}
