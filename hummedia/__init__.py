import re
import sys

from flask import Flask
app = Flask(__name__)

# Are we running py.test?
if re.match(r'.*py\.test$', sys.argv[0], re.MULTILINE):
    # if py.test is running this, overwrite configuration values
    import config
    from tempfile import mkdtemp
    from os import sep

    patch = {
        'MONGODB_DB': 'hummedia_test',
        'SUBTITLE_DIRECTORY': mkdtemp('hummedia-subs') + sep,
        'MEDIA_DIRECTORY': mkdtemp('hummedia-media') + sep,
        'AUTH_TOKEN_IP': False,
        'INGEST_DIRECTORY': mkdtemp('hummedia-ingest') + sep,
        'POSTERS_DIRECTORY': mkdtemp('hummedia-posters') + sep,
        'APIHOST': '',
        'HOST': '',
    }

    for name, value in patch.items():
        setattr(config, name, value)


import hummedia.api  # noqa: E402
import hummedia.auth  # noqa: E402,F401
