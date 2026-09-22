#!/bin/sh

TMP_FILE=$(mktemp)
if /usr/bin/openssl dhparam -out $TMP_FILE 2048 2> /dev/null; then
    rm -f /etc/ssl/dhparam.pem
    mv $TMP_FILE /etc/ssl/dhparam.pem
    /bin/systemctl reload nginx
fi

