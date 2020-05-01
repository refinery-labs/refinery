#!/bin/bash
echo "Rebuilding all Lambda layers..."
cd go1.12/
./build.sh
cd ../
cd node10.16.3/
./build.sh
cd ../
cd node10.20.1/
./build.sh
cd ../
cd node8.10/
./build.sh
cd ../
cd node10.20.1/
./build.sh
cd ../
cd php7.3/
./build.sh
cd ../
cd python2.7/
./build.sh
cd ../
cd python3.6/
./build.sh
cd ../
cd ruby2.6.4/
./build.sh
cd ../
