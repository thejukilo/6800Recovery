#!/bin/bash
set -e

# Create new log file
log_directory=/opt/roche/var/lib/mollab/shared/logs
log_prefix=Instrument_
log_extension=.log
log_file=$log_directory/${log_prefix}$(date +%Y%m%d)${log_extension}
touch "$log_file"

# Setup the logging
exec 1> >(while read -r line; do echo "[$(date -u +%FT%T.%NZ)][MI][I][Instrument][0]${line//$'\r'}[EOL]"; done >> "$log_file") 2>&1

# Purge old log files
log_retention=7 # Number of log files to keep, including the current one
find "$log_directory" -maxdepth 1 -type f -name "${log_prefix}*${log_extension}" | sort | head --lines=-$log_retention | xargs rm -f
