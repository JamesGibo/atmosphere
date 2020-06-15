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

from atmosphere import app


class TestApp:
    def test_sqlalchemy_database_uri_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URI", "foobar")

        test_app = app.create_app()
        assert test_app.config['SQLALCHEMY_DATABASE_URI'] == 'foobar'

    def test_debug_enables_sqlalchemy_echo(self):
        class FakeConfig:
            DEBUG = True

        test_app = app.create_app(FakeConfig)
        assert test_app.config['SQLALCHEMY_ECHO'] == True
