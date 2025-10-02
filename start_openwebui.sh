#!/bin/bash
cd /home/linuxuser/openwebui
source venv/bin/activate
export $(cat .env | xargs)
python -m open_webui.main
