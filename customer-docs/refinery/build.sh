echo "Building site..."
mkdocs build
echo "Syncing site to S3..."
s3cmd sync --acl-public --delete-removed ./site/ s3://docs.refinery.io/
