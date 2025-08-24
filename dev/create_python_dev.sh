#!/bin/bash

cd /workspace/hysteretic_olm

python3 -m venv venv
ln -s /workspace/build/opensees.so /workspace/hysteretic_olm/venv/lib/python3.10/site-packages/opensees.so

source venv/bin/activate

pip install -r requirements.txt
