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

from atmosphere.tests.unit import fake
from atmosphere import models


@pytest.mark.usefixtures("client", "db_session")
class TestEvent:
    def test_with_no_json_provided(self, client):
        response = client.post('/v1/event')

        assert response.status_code == 400

    def test_with_one_event_provided(self, client):
        event = fake.get_event()
        response = client.post('/v1/event', json=[event])

        assert response.status_code == 204
        assert models.Resource.query.count() == 1
        assert models.Period.query.count() == 1
        assert models.Spec.query.count() == 1

    def test_with_multiple_events_provided(self, client):
        event_1 = fake.get_event(resource_id='fake-resource-1')
        event_2 = fake.get_event(resource_id='fake-resource-2')

        response = client.post('/v1/event', json=[event_1, event_2])

        assert response.status_code == 204
        assert models.Resource.query.count() == 2
        assert models.Period.query.count() == 2
        assert models.Spec.query.count() == 1

    def test_with_old_event_provided(self, client):
        event_new = fake.get_event()
        event_new['generated'] = '2020-06-07T01:42:54.736337'
        response = client.post('/v1/event', json=[event_new])

        assert response.status_code == 204
        assert models.Resource.query.count() == 1
        assert models.Period.query.count() == 1
        assert models.Spec.query.count() == 1

        event_old = fake.get_event()
        event_old['generated'] = '2020-06-07T01:40:54.736337'
        response = client.post('/v1/event', json=[event_old])

        assert response.status_code == 202
        assert models.Resource.query.count() == 1
        assert models.Period.query.count() == 1
        assert models.Spec.query.count() == 1

    def test_with_invalid_event_provided(self, client):
        event = fake.get_event(event_type='foo.bar.exists')
        response = client.post('/v1/event', json=[event])

        assert response.status_code == 400
        assert models.Resource.query.count() == 0
        assert models.Period.query.count() == 0
        assert models.Spec.query.count() == 0

    def test_with_ignored_event_provided(self, client, ignored_event):
        event = fake.get_event(event_type=ignored_event)
        response = client.post('/v1/event', json=[event])

        assert response.status_code == 202
        assert models.Resource.query.count() == 0
        assert models.Period.query.count() == 0
        assert models.Spec.query.count() == 0
