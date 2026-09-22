#!/bin/bash
set -e

#Startup Selenium server standalone on port 4444
cd /opt/roche/home
export DISPLAY=":0"
/opt/roche/home/java/openlogic-openjdk-jre-17.0.10+7-linux-x64/bin/java -jar selenium-server-4.20.0.jar standalone --port 4444 --config selenium-server-config.toml

wait