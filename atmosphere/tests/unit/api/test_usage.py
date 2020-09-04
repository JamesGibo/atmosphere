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

from dateutil.relativedelta import relativedelta
import pytest

from atmosphere.api import usage
from atmosphere.tests.unit import fake
from atmosphere import models
from atmosphere.models import db


@pytest.fixture
def app():
    app = usage.init_application()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_ECHO'] = True
    return app


@pytest.mark.usefixtures("client")
class TestResourceNoAuth:
    def test_get_resources(self, client):
        response = client.get('/v1/resources')

        assert response.status_code == 401
