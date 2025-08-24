#!/bin/bash

mkdir -p /workspace/build
cd /workspace/build
conan install .. --build missing
cmake .. -DMUMPS_DIR=/usr/local/mumps
cmake --build . --target OpenSees -j8
cmake --build . --target OpenSeesPy -j8
mv ./lib/OpenSeesPy.so ./opensees.so
