<!-- markdown-extras: code-friendly, footnotes, fenced-code-blocks -->
gitreload
=========
[![Build Status](http://img.shields.io/travis/mitodl/gitreload.svg?style=flat)](https://travis-ci.org/mitodl/gitreload)
[![Coverage Status](http://img.shields.io/coveralls/mitodl/gitreload.svg?style=flat)](https://coveralls.io/r/mitodl/gitreload)
[![PyPi Downloads](http://img.shields.io/pypi/dm/gitreload.svg?style=flat)](https://pypi.python.org/pypi/gitreload)
[![PyPi Version](http://img.shields.io/pypi/v/gitreload.svg?style=flat)](https://pypi.python.org/pypi/gitreload)
[![License AGPLv3](http://img.shields.io/badge/license-AGPv3-blue.svg?style=flat)](http://www.gnu.org/licenses/agpl-3.0.html)

gitreload is a Flask/WSGI application for responding to github
triggers asynchronously.  Out of the box it is primarily intended for
use with the [edx-platform](https://github.com/edx/edx-platform), but
could be used for generally updating local git repositories based on a
trigger call from github using its `/update` url.

The general workflow is that a github trigger is received (push),
gitreload checks if the respository and branch are already checked
out in the configured location, and then either
imports that repository into the edx-platform via a `... manage.py lms
--settings=... git_add_course <repo_dir> <repo_name>` command, or if
the trigger is set to go to `/update` instead of `/` or `/gitreload`,
it will simply fetch the newset version of the currently checked out
branch from the `origin` remote. Authorization is generally expected
to be provided by the Web server in front of it (using basic
authentication), as it currently doesn't support the use of github
secrets. An additional layer of security is provided by the fact that
a repository must be cloned on gitreload's host before it will accept
payloads from github for said repository.

## Installation ##

`pip install gitreload`

or to use the latest github version it would
be:

`pip install -e git+https://github.com/mitodl/gitreload`

## Usage ##

gitreload is a flask application, and thus can be run either in debug
mode by directly using the `gitreload` command, or by
using a wsgi application server.  For more information on running a
flask app in a production mode, see the excellent
[flask documentation](http://flask.pocoo.org/docs/0.10/deploying/wsgi-standalone/).
We generally have run it using gunicorn and supervisord in a similar
manner that [edx/configuration](https://github.com/edx/configuration)
roles follow, and eventually we plan on submitting a role to install
this via their ansible plays.

Upon running `gitreload` via command line, you should see that it
starts up listening on port 5000. You can verify that it is working by
going to the queue status page at `http://localhost:5000/queue`.
If all is well, you should be greeted with some lovely json that looks
like:

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

## Use Cases ##

This is currently in use at MITx primarily for the following reasons.

### Rapid Centralized Course Development ###

One of our primary uses of this tool is to enable rapid shared XML
based edx-platform course development.  It is basically the continuous
integration piece for our courseware, such that when a commit gets
pushed to a github repo on a specific branch (say devel), the changes
are quickly and automatically loaded up with the use of this hook
consumer.

### Course Deployment Management ###

Along the lines of the rapid course development, we also use this
method for controlling which courses get published on our production
student facing LMS.  For raw github XML developers, this means that we
hook up our student facing LMS to a specific branch intended for
production (say master or release). We use this to monitor that branch
for changes they have vetted in their development branch and are ready
to deploy to students.

We don't limit our usage of gitreload to XML development though, as we
also gate our Studio course teams with this same method. There is a
feature in the platform that allows course teams to export their course
to Git. We use this function to control student access, allowing our
Studio course authors to push at will to production once the trigger
and repositories are setup for their course.

### Update of external course graders ###

We use the regular `/update` feature to automatically update external
code graders that are served via
[xqueue-watcher](https://github.com/edx/xqueue-watcher) or
[xserver](https://github.com/edx/xserver).  We use this in a similar
vain as the previous two cases and manages a development and
production branch for the repository that contains the graders.
