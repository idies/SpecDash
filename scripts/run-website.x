#!/bin/bash
cd /var/www/specdash/prod/specdash/
source ./venv/bin/activate
gunicorn --workers 4 --bind 0.0.0.0:5010 --timeout 60  specdash_website:server
