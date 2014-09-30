<!-- markdown-extras: code-friendly, footnotes, fenced-code-blocks -->
gitreload
=========
[![Build Status](http://img.shields.io/travis/mitodl/gitreload.svg?style=flat)](https://travis-ci.org/mitodl/gitreload)
[![Coverage Status](https://coveralls.io/repos/mitodl/gitreload/badge.png?branch=master)](https://coveralls.io/r/mitodl/gitreload)
[![PyPi Downloads](http://img.shields.io/pypi/dm/gitreload.svg?style=flat)](https://pypi.python.org/pypi/gitreload)
[![PyPi Version](http://img.shields.io/pypi/v/gitreload.svg?style=flat)](https://pypi.python.org/pypi/gitreload)

gitreload is a Flask/WSGI application for responding to github
triggers asynchronously.  Out of the box it is primarily intended for
use with the [edx-platform](https://github.com/edx/edx-platform) but
could be used for generally updating of local git repositories based on a
trigger call from github using it's `/update` url.

The general workflow is that a github trigger is received (push),
gitreload checks that the respository and branch are already checked
out in the configured location, and then either runs a command to
import that repository into the edx-platform via a `... manage.py lms
--settings=... git_add_course <repo_dir> <repo_name>` command, or if
the trigger is set to go to `/update` instead of `/` or `/gitreload`
it will simply fetch the newset version of the currently checked out
branch from the `origin` remote. Authorization is generally expected
to be provided by the Web server infront of it using basic
authentication as it currently doesn't support using github secrets,
but also requiring the repository to already be cloned add additional
authorization.

## Installation ##

`pip install gitreload`

or to use the latest github version it would
be:

`pip install -e git+https://github.com/mitodl/gitreload`

## Usage ##

gitreload is a flask application and thus can be run by either
directly with the `gitreload` command to run it in a debug mode or by
using a wsgi application server.  For more information on running a
flask app in a production mode see the excellent
[flask documentation](http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/).
We generally have run it using gunicorn and supervisord in a similar
manner that [edx/configuration](https://github.com/edx/configuration)
roles follow, and eventually we plan on submitting a role to install
this via their ansible plays.

If running via command line `gitreload` you should see that it started
up listening on port 5000. You can verify it is working by going to
the queue status page at `http://localhost:5000/queue` and you should
be greeted with some lovely json that looks like:

```javascript
{"queue_length": 0, "queue": []}
```

## Configuration ##

Configuration is done via a json file stored in order of precedence:

- Path in environment variable: `GITRELOAD_CONFIG`
- $(pwd)/gr.env.json
- ~/gr.env.json
- /etc/gr.env.json

It isn't strictly required, and the defaults are:

```javascript
{
    "DJANGO_SETTINGS": "aws",
    "EDX_PLATFORM": "/edx/app/edxapp/edx-platform",
    "LOG_LEVEL": null,
    "NUM_THREADS": 1,
    "REPODIR": "/mnt/data/repos",
    "VIRTUAL_ENV": "/edx/app/edxapp/venvs/edxapp"
}
```

This setup means that it looks for the git repositories to be cloned
in `/mnt/data/repos`, and expects the edx-platform settings to be the
current [edx/configuration](https://github.com/edx/configuration)
defaults.  It also leaves the LOG_LEVEL set to the default which
is `WARNING`, and provides only one worker thread to process the
queue of received triggers from github.

