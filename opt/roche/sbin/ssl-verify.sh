#!/bin/sh

filename="$1"
signature="$2"

if [ -z "$filename" -o -z "$signature" ]; then
    echo Usage: $0 file signature >&2
    exit 1
fi

CA_CERTS="/opt/roche/ssl/codesign-CA.pem"
SIGN_CERT="/opt/roche/ssl/codesign-CERT.pem"

openssl verify -CAfile "$CA_CERTS" "$SIGN_CERT" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo Error verifying CA and CERT >&2
    exit 2
fi

sign_algo=$(openssl x509 -in "$SIGN_CERT" -noout -text | grep "Signature Algorithm:" | cut -d':' -f2)
for a in $sign_algo; do
    if [ $a = "sha512WithRSAEncryption" ]; then
        OPT_ALGO="-sha512"
        break
    elif [ $a = "sha384WithRSAEncryption" ]; then
        OPT_ALGO="-sha384"
        break
    elif [ $a = "sha256WithRSAEncryption" ]; then
        OPT_ALGO="-sha256"
        break
    elif [ $a = "sha1WithRSAEncryption" ]; then
        OPT_ALGO="-sha1"
        break
    elif [ $a = "ecdsa-with-SHA512" ]; then
        OPT_ALGO="-sha512"
        break
    elif [ $a = "ecdsa-with-SHA384" ]; then
        OPT_ALGO="-sha384"
        break
    elif [ $a = "ecdsa-with-SHA256" ]; then
        OPT_ALGO="-sha256"
        break
    fi
done

pubkey=`mktemp`
openssl x509 -in "$SIGN_CERT" -pubkey -noout > $pubkey 2>/dev/null
if [ $? -ne 0 ]; then
    echo Error extracting public key >&2
    exit 3
fi
openssl dgst $OPT_ALGO -verify $pubkey -signature "$signature" "$filename" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo Error: Signature is not valid >&2
    exit 4
fi
rm -f $pubkey
