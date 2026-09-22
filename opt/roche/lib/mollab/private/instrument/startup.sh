#!/bin/bash
set -e

source /opt/roche/lib/mollab/private/instrument/logging.sh

echo "Loading env vars"
ENV_FOLDER=/opt/roche/home/profile.d
if [ -d "$ENV_FOLDER" ]; then
  for i in $(ls "$ENV_FOLDER"/*.sh); do
    . $i
  done
  unset i
fi

echo "Execute unit startup scripts"
# use subshell to avoid changing the current directory, and we want to change it to reduce the path length in the logs
(
  cd /opt/roche/lib/mollab/private/instrument/ &&
  run-parts --verbose startup.d
)
echo "Unit startup scripts completed"