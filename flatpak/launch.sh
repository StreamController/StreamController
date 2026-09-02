#!/bin/bash
export GI_TYPELIB_PATH=/app/lib64/girepository-1.0:/app/lib/girepository-1.0:$GI_TYPELIB_PATH
export LD_LIBRARY_PATH=/app/lib64:/app/lib:$LD_LIBRARY_PATH
cd /app/bin/StreamController
python3 /app/bin/StreamController/main.py "$@"