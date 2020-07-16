#!/bin/bash
echo "Building Ruby 2.6.4 Refinery custom runtime layer package..."
mkdir -p ./layer-contents
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../../base-src/* ./layer-contents/
cp -r ./ruby ./layer-contents/
cp -r ./lib64 ./layer-contents/
cp runtime ./layer-contents/
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf ./layer-contents/*
