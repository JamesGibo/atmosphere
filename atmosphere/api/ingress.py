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

"""Ingress

"""

from flask import Blueprint
from flask import request
from flask import abort
from flask import jsonify

from atmosphere.app import create_app
from atmosphere import exceptions
from atmosphere import utils
from atmosphere import models

blueprint = Blueprint('ingress', __name__)


def init_application(config=None):
    """init_application"""
    app = create_app(config)
    app.register_blueprint(blueprint)
    return app


@blueprint.route('/v1/event', methods=['POST'])
def event():
    """event"""
    if request.json is None:
        abort(400)

    for event_data in request.json:
        print(jsonify(event_data).get_data(True))
        event_data = utils.normalize_event(event_data)

        try:
            models.Resource.get_or_create(event_data)
        except exceptions.EventTooOld:
            return 'Event Too Old', 202
        except exceptions.IgnoredEvent:
            return 'Ignored Event', 202

    return '', 204
