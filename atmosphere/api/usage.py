# Copyright 2020 VEXXHOST, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Usage API."""

import os
from datetime import datetime

from flask import abort
from flask import Blueprint
from flask import request
from flask import jsonify
from keystonemiddleware import auth_token
from oslo_config import cfg

from atmosphere.app import create_app
from atmosphere import models

CONF = cfg.CONF
CONFIG_FILES = ['atmosphere.conf']


blueprint = Blueprint('usage', __name__)


def _get_config_files(env=None):
    if env is None:
        env = os.environ
    dirname = env.get('OS_ATMOSPHERE_CONFIG_DIR', '/etc/atmosphere').strip()
    return [os.path.join(dirname, config_file) for config_file in CONFIG_FILES]


def init_application(config=None):
    """Create usage API application."""
    app = create_app(config)
    app.register_blueprint(blueprint)

    conf_files = _get_config_files()
    cfg.CONF([], project='atmosphere', default_config_files=conf_files)

    authtoken_config = dict(CONF.keystone_authtoken)
    authtoken_config['log_name'] = app.name

    app.wsgi_app = auth_token.AuthProtocol(app.wsgi_app, authtoken_config)
    return app


@blueprint.route('/v1/resources')
def list_resources():
    """List all resources for a specific project."""
    # Project ID from request (or allow override if admin)
    project_id = request.headers['X-Project-Id']
    if 'admin' in request.headers['X-Roles'] and 'project_id' in request.args:
        project_id = request.args['project_id']

    try:
        start = datetime.fromisoformat(request.args['start'])
        end = datetime.fromisoformat(request.args['end'])
    except (KeyError, ValueError):
        abort(400)

    resources = models.Resource.get_all_by_time_range(start, end, project_id)
    return jsonify([r.serialize for r in resources])
