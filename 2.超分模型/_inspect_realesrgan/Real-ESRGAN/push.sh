#!/bin/bash
REMOTE_USER="sunwei"
REMOTE_HOST="10.0.11.22"
REMOTE_DEST="/home/sunwei/Real-ESRGAN/"
SSH_PORT="22"
rsync -avzP -e "ssh -p ${SSH_PORT}" "$@" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DEST}"
