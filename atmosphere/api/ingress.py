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

from flask import Blueprint
from flask import request
from flask import abort
from flask import jsonify
from dateutil.relativedelta import relativedelta

from atmosphere.app import create_app
from atmosphere import exceptions
from atmosphere import utils
from atmosphere import models

blueprint = Blueprint('ingress', __name__)


def init_application(config=None):
    app = create_app(config)
    app.register_blueprint(blueprint)
    return app


@blueprint.route('/v1/event', methods=['POST'])
def event():
    if request.json is None:
        abort(400)

    for event in request.json:
        print(jsonify(event).get_data(True))
        event = utils.normalize_event(event)

        try:
            resource = models.Resource.get_or_create(event)
        except (exceptions.EventTooOld, exceptions.IgnoredEvent):
            return '', 202

        # TODO(mnaser): Drop this logging eventually...
        print(jsonify(event).get_data(True))
        print(jsonify(resource.serialize).get_data(True))

    return '', 204
