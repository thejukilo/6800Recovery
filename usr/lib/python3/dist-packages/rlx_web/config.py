'''RLX Web config

RLX is configured via an optional ini file in:
/opt/roche/etc/rlx-web.ini

Use like this:

    from rlx_web.config import config
    config.get('foo', 'bar', fallback='baz')

See also https://docs.python.org/3/library/configparser.html

Example file:

    [rancher]
    image = full.url.of/some-docker-image:tag

'''
import configparser

RLX_WEB_CONFIG_FILENAME = '/opt/roche/etc/rlx-web.ini'

config = configparser.ConfigParser()
config.read(RLX_WEB_CONFIG_FILENAME)
