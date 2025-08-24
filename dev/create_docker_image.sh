#!/bin/bash
docker build --platform linux/amd64 -t opensees-dev -f Dockerfile.dev .
