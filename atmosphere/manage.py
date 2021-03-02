# Copyright 2021 BBC.
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

"""Manage

"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand


app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if app.config.get('SQLALCHEMY_DATABASE_URI') is None:
    app.config['SQLALCHEMY_DATABASE_URI'] = \
            os.environ.get('DATABASE_URI', 'sqlite:///:memory:')

MIGRATION_DIR = os.path.join(os.path.dirname(__file__), 'migrations')

db = SQLAlchemy(app)
migrate = Migrate(app, db, directory=MIGRATION_DIR)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


def main():
    """main"""
    manager.run()


if __name__ == '__main__':
    main()
