#!/bin/sh

CERTS=`cat /etc/roche.certs`

DIR=`mktemp -d /tmp/roche-certs-XXXX`
chmod 755 $DIR
cd $DIR

for cert in $CERTS
do
  echo $cert
  wget -q $cert
done
cd

cp -f $DIR/* /usr/local/share/ca-certificates/
update-ca-certificates

# If there are no parameters then install the browser certificates too...
if [ $# -eq 0 ]
then
  ROCHEHOME=`getent passwd roche | cut -d: -f6`
  SEARCH="$ROCHEHOME/.pki/nssdb"
  if [ -d $ROCHEHOME/.mozilla ]; then
    SEARCH="$SEARCH $ROCHEHOME/.mozilla/"
  fi

  for i in `find $SEARCH -name cert9.db`
  do
    certdir=`dirname $i`;
    echo Installing into $certdir
    for j in $DIR/*
    do
      echo "Adding: $j"
      su roche -c "certutil -d sql:$certdir -A -t \"TCu,Cuw,Tuw\" -n \"$j\" -i \"$j\""
    done
  done
fi

rm -rf $DIR
