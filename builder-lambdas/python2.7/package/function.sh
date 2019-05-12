function handler () {
  export PATH="$(pwd)/bin/:$PATH"
  export PYTHONPATH="$LAMBDA_TASK_ROOT/lib/python2.7/site-packages/"
  export LD_LIBRARY_PATH="$(pwd)/bin/"
  EVENT_DATA=$1
  
  # Clear out previous build directory
  rm -rf /tmp/build/
  
  # Create new build directory
  mkdir /tmp/build/
  
  # Get a straight string of the libraries (\n seperated)
  # for requirements.txt
  LIBRARIES_LINES=$(echo -n "$1" | jq .libraries | jq -r .[] )
  
  # Get a JSON sorted and minified version of the libraries
  # so we can use it for a key for the hash function
  LIBRARIES_JSON=$(echo -n "$1" | jq .libraries | jq -c "sort")
  
  # Creates a hash for S3 which we can use to immediately return
  # already generated library packages.
  LIBRARIES_HASH=$(echo -n "python-$LIBRARIES_JSON" | sha256sum | awk -F" " '{print $1}' )
  
  # Generate S3 object path
  S3_OBJECT_PATH="$LIBRARIES_HASH.zip"
  
  # Generate S3 full path
  PACKAGE_S3_PATH="s3://$BUILD_BUCKET/$S3_OBJECT_PATH"
  
  echo "Checking S3 bucket for a previously-cached build..." 1>&2;
  
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
  
  # Write new requirements.txt
  echo "$LIBRARIES_LINES" > /tmp/build/requirements.txt
  
  # Cat requirements.txt
  cat /tmp/build/requirements.txt 1>&2;
  
  # Create a new virtualenv in the build directory
  virtualenv /tmp/build/ 1>&2;
  
  # Source the new virtualenv
  source /tmp/build/bin/activate
  
  # Install libraries in virtualenv
  pip install -r /tmp/build/requirements.txt 1>&2;
  
  cd /tmp/build/lib/python2.7/site-packages/
  
  zip -r libraries.zip * 1>&2;
  
  mv libraries.zip /tmp/build/
  
  python "$LAMBDA_TASK_ROOT/lib/python2.7/site-packages/awscli/__main__.py" s3 cp /tmp/build/libraries.zip "$PACKAGE_S3_PATH" 1>&2;

  echo $PACKAGE_S3_PATH
}
