#!/bin/bash

if [ -d "./node_modules" ]; then
  echo "Deleting node modules"
  rm -rf ./node_modules
fi

echo "Copying node modules"
cp -r /work/front-end-modules/node_modules /work/front-end/

echo "Done!"
