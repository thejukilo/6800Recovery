#!/bin/bash
set -e

if pgrep ui.browser; then
  pkill ui.browser
fi

sleep 1

Xorg :0 &

wait