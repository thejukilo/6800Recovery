#!/bin/bash
set -e

source /opt/roche/lib/mollab/private/instrument/logging.sh

echo "Execute shutdown scripts"
# use subshell to avoid changing the current directory, and we want to change it to reduce the path length in the logs
(
  cd /opt/roche/lib/mollab/private/instrument/ &&
  run-parts --verbose shutdown.d
)
echo "Unit shutdown scripts completed"