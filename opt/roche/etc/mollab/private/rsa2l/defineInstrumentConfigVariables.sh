#!/bin/sh

# This script is used to set project specific rsa2l configuration variables.
# rsa2l documentation: https://sites.google.com/contractors.roche.com/rsa2l/configuration

# MANDATORY variables to set:
# InstrumentConfig_RoutingType

if [ -n "$MolLab_InstrumentType" ]
  then
  # RoutingType: c6800IM or c8800IM
  case $MolLab_InstrumentType in 
      *6800*) InstrumentConfig_RoutingType="c6800IM";;
      *8800*) InstrumentConfig_RoutingType="c8800IM";;
      *) echo 'ERROR: Invalid InstrumentType: ' $MolLab_InstrumentType;;
  esac
else
  echo 'ERROR: Invalid data for adapting the config file. InstrumentType:' $MolLab_InstrumentType 
  exit 1
fi
echo "Set RoutingType to: $InstrumentConfig_RoutingType"