#!/bin/bash
export GI_TYPELIB_PATH=/app/lib64/girepository-1.0:/app/lib/girepository-1.0:$GI_TYPELIB_PATH
cd /app/bin/StreamController
python3 /app/bin/StreamController/main.py "$@"