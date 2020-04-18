#!/bin/bash
echo "Building Node 10.16.3 Refinery custom runtime layer package..."
mkdir -p ./layer-contents;
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf /layer-contents/*
