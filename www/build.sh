source env/bin/activate
echo "Building site..."
jekyll build

rm -rf ./_site/build.sh
rm -rf ./_site/env/
rm -rf ./_site/serve.sh
rm -rf ./_site/LICENSE.txt
rm -rf ./_site/README.md

echo "Syncing site to S3..."
s3cmd sync --acl-public --delete-removed ./_site/ s3://www.refinerylabs.io/
deactivate
