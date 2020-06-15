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

import pytest

from flask_sqlalchemy import SQLAlchemy

from atmosphere.app import create_app
from atmosphere.api import ingress
from atmosphere.models import db


@pytest.fixture(params=[
    'aggregate.cache_images.progress',
    'compute_task.build_instances.error',
    'compute.exception',
    'flavor.create',
    'keypair.create.end',
    'libvirt.connect.error',
    'metrics.update',
    'scheduler.select_destinations.end',
    'server_group.add_member',
    'service.create',
    'volume.usage',
])
def ignored_event(request):
    yield request.param


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.register_blueprint(ingress.blueprint)
    return app


@pytest.fixture
def _db(app):
    db.init_app(app)
    db.create_all()
    return db
