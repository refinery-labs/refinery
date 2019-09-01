#!/bin/bash
echo "Building Ruby 2.6.4 Refinery custom runtime layer package..."
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cp -r ./ruby/ ./layer-contents/
cp -r ./lib/ ./layer-contents/
cp runtime ./layer-contents/
cd ./layer-contents/
zip -r custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf ./layer-contents/*
