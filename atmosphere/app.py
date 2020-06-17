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

"""App

"""
import os

from flask import Flask

from atmosphere import models


def create_app(config=None):
    """create_app"""
    app = Flask(__name__)

    if config is not None:
        app.config.from_object(config)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if app.config.get('SQLALCHEMY_DATABASE_URI') is None:
        app.config['SQLALCHEMY_DATABASE_URI'] = \
                os.environ.get('DATABASE_URI', 'sqlite:///:memory:')
    if app.config['DEBUG']:
        app.config['SQLALCHEMY_ECHO'] = True

    models.db.init_app(app)

    package_dir = os.path.abspath(os.path.dirname(__file__))
    migrations_path = os.path.join(package_dir, 'migrations')
    models.migrate.init_app(app, models.db, directory=migrations_path)

    return app
