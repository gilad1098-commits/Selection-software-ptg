#!/bin/bash
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
