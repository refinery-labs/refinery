#!/bin/bash
echo "Building Node 10.16.3 Refinery custom runtime layer package..."
<<<<<<< HEAD
mkdir -p ./layer-contents
=======
mkdir -p ./layer-contents;
>>>>>>> master
rm -rf ./layer-contents/*
cp runtime ./layer-contents/
cp -r ../base-src/* ./layer-contents/
cd ./layer-contents/
zip -qr custom-runtime.zip *
mv custom-runtime.zip ../
cd ..
rm -rf /layer-contents/*
