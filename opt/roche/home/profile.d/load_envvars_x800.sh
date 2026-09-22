#!/bin/sh

# Fix up instrument type as this is what is expected from the containers
if [ "${MolLab_InstrumentType:?}" = "6800" ]; then
  ExportEnvVar MolLab_InstrumentType "${MolLab_InstrumentType}_${x800_AnalyticCyclersCount:?}AC"
fi

# Default GTIN number
gtinnumber="07613336175200"

#SetUp GTIN number
if [ -n "$MolLab_SerialNumber" ]; then

    gtincobas6800v1=04015630935406
    gtincobas6800v2=07613336206355
    gtincobas8800v1=04015630935390
    gtincobas8800v2=07613336206362

    echo "Determine the gtin value based on the value of serialnumber"
    if [ "$MolLab_SerialNumber" -ge 50000 ]; then
        gtinnumber=$gtincobas8800v2
    elif [ "$MolLab_SerialNumber" -ge 10000 ]; then
        gtinnumber=$gtincobas6800v2
    elif [ "$MolLab_SerialNumber" -ge 5000 ]; then
        gtinnumber=$gtincobas8800v1
    elif [ "$MolLab_SerialNumber" -ge 1000 ]; then
        gtinnumber=$gtincobas6800v1
    fi
fi
ExportEnvVar MolLab_Gtin $gtinnumber
