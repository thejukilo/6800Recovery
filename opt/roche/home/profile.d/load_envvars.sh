#!/bin/sh

ExportEnvVar() {
  VariableName=$1
  Value=$2
  export "$VariableName=$Value"
  echo "Setting env var '$VariableName' to '$Value'"
}

# hardcode RLX special paths
ExportEnvVar MolLab_InstrumentType "$(cat /opt/roche/etc/instrument-type)"
ExportEnvVar MolLab_SerialNumber "$(cat /opt/roche/etc/serial-number)"

# iterate all env files and export as variables with the same name and the content as value
for Filename in /opt/roche/var/lib/mollab/shared/device-config/*.env /opt/roche/etc/mollab/shared/device-config/*.env; do
  # skip nonexistent files (mostly to avoid globbing returning no files)
  [ -f "$Filename" ] || continue;

  # export the variable/value
  ExportEnvVar "$(basename -s .env "$Filename")" "$(cat "$Filename")"
done