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

import datetime
from unittest import mock

import pytest
from sqlalchemy import exc
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
import before_after

from atmosphere import models
from atmosphere import exceptions
from atmosphere.tests.unit import fake


class GetOrCreateTestMixin:
    def test_with_existing_object(self):
        event = fake.get_normalized_event()
        assert self.MODEL.query_from_event(event).count() == 0

        old_object = self.MODEL.get_or_create(event)
        assert self.MODEL.query_from_event(event).count() == 1

        new_object = self.MODEL.get_or_create(event)
        assert self.MODEL.query_from_event(event).count() == 1

        assert old_object == new_object

    def test_with_no_existing_object(self):
        event = fake.get_normalized_event()
        assert self.MODEL.query_from_event(event).count() == 0

        new_object = self.MODEL.get_or_create(event)
        assert self.MODEL.query_from_event(event).count() == 1

    def test_with_object_created_during_creation(self):
        event = fake.get_normalized_event()
        assert self.MODEL.query_from_event(event).count() == 0

        def before_session_begin(*args, **kwargs):
            self.MODEL.get_or_create(event)
        with before_after.before('atmosphere.models.db.session.begin',
                                 before_session_begin):
            self.MODEL.get_or_create(event)

        assert self.MODEL.query_from_event(event).count() == 1


@pytest.mark.usefixtures("db_session")
class TestResource(GetOrCreateTestMixin):
    MODEL = models.Resource

    def test_from_event(self):
        event = fake.get_normalized_event()
        resource = models.Resource.from_event(event)

        assert resource.uuid == event['traits']['resource_id']
        assert resource.project == event['traits']['project_id']
        assert resource.updated_at == event['generated']

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    def test_query_from_event(self, mock_query_property_getter):
        mock_filter_by = mock_query_property_getter.return_value.filter_by

        event = fake.get_normalized_event()
        query = models.Resource.query_from_event(event)

        mock_filter_by.assert_called_with(
            project='fake-project',
            uuid='fake-uuid',
        )

    def test_get_or_create_with_old_event(self):
        event = fake.get_normalized_event()
        new_object = models.Resource.get_or_create(event)

        old_event = event.copy()
        old_event['generated'] = event['generated'] + \
            relativedelta(microseconds=-1)

        with pytest.raises(exceptions.EventTooOld) as e:
            models.Resource.get_or_create(old_event)

    def test_get_or_create_refresh_updated_at(self):
        event = fake.get_normalized_event()
        old_object = models.Resource.get_or_create(event)

        new_event = event.copy()
        new_event['generated'] = event['generated'] + \
            relativedelta(microseconds=+1)

        new_object = models.Resource.get_or_create(new_event)

        assert new_object.updated_at == new_event['generated']
        assert models.Resource.query_from_event(event).count() == 1

    def test_get_or_create_using_created_at(self):
        event = fake.get_normalized_event()
        resource = models.Resource.get_or_create(event)

        assert resource.get_open_period().started_at == \
            event['traits']['created_at']

    def test_get_or_create_using_deleted_event_only(self):
        event = fake.get_normalized_event()
        event['traits']['deleted_at'] = event['traits']['created_at'] + \
            relativedelta(hours=+1)

        resource = models.Resource.get_or_create(event)

        assert resource.get_open_period() is None
        assert len(resource.periods) == 1
        assert resource.periods[0].ended_at == event['traits']['deleted_at']
        assert resource.periods[0].seconds == 3600

    def test_get_or_create_using_multiple_deleted_events(self):
        event = fake.get_normalized_event()
        event['traits']['deleted_at'] = event['traits']['created_at'] + \
            relativedelta(hours=+1)

        models.Resource.get_or_create(event)
        with pytest.raises(exceptions.EventTooOld) as e:
            models.Resource.get_or_create(event)

    def test_get_or_create_using_deleted_event(self):
        event = fake.get_normalized_event()
        old_resource = models.Resource.get_or_create(event)

        assert old_resource.get_open_period() is not None
        assert len(old_resource.periods) == 1

        event['traits']['deleted_at'] = event['traits']['created_at'] + \
            relativedelta(hours=+1)
        new_resource = models.Resource.get_or_create(event)

        assert old_resource == new_resource
        assert new_resource.get_open_period() is None
        assert len(new_resource.periods) == 1
        assert new_resource.periods[0].ended_at == \
            event['traits']['deleted_at']
        assert new_resource.periods[0].seconds == 3600

    def test_get_or_create_using_updated_spec(self):
        event = fake.get_normalized_event()
        old_resource = models.Resource.get_or_create(event)

        assert old_resource.get_open_period() is not None
        assert len(old_resource.periods) == 1

        event['traits']['instance_type'] = 'v1-standard-2'
        event['generated'] += relativedelta(hours=+1)
        new_resource = models.Resource.get_or_create(event)

        assert old_resource == new_resource
        assert new_resource.get_open_period() is not None
        assert len(new_resource.periods) == 2

        assert new_resource.periods[0].ended_at == event['generated']
        assert new_resource.get_open_period().started_at == event['generated']

    def test_get_or_create_using_same_spec(self):
        event = fake.get_normalized_event()
        old_resource = models.Resource.get_or_create(event)

        assert old_resource.get_open_period() is not None
        assert len(old_resource.periods) == 1

        event['generated'] += relativedelta(hours=+1)
        new_resource = models.Resource.get_or_create(event)

        assert old_resource == new_resource
        assert old_resource.periods == new_resource.periods
        assert new_resource.get_open_period() is not None
        assert len(new_resource.periods) == 1

    def test_serialize_with_no_periods(self):
        resource = fake.get_resource()

        assert resource.serialize == {
            'uuid': resource.uuid,
            'type': resource.type,
            'project': resource.project,
            'updated_at': resource.updated_at,
            'periods': [],
        }

    def test_serialize(self):
        resource = fake.get_resource_with_periods(20)

        assert resource.serialize == {
            'uuid': resource.uuid,
            'type': resource.type,
            'project': resource.project,
            'updated_at': resource.updated_at,
            'periods': [p.serialize for p in resource.periods],
        }

    def test_number_of_periods_with_no_periods(self):
        resource = fake.get_resource_with_periods(0)
        models.db.session.add(resource)
        models.db.session.commit()

        assert len(resource.periods) == 0

    def test_number_of_periods_with_periods(self):
        resource = fake.get_resource_with_periods(20)
        models.db.session.add(resource)
        models.db.session.commit()

        assert len(resource.periods) == 20

    def test_get_open_period_with_no_open(self):
        resource = fake.get_resource_with_periods(20)
        models.db.session.add(resource)
        models.db.session.commit()

        assert resource.get_open_period() is None

    def test_get_open_period_with_only_one_open_period(self):
        resource = fake.get_resource()
        spec = fake.get_instance_spec()

        period = models.Period(spec=spec)
        period.started_at = datetime.datetime.now()
        resource.periods.append(period)

        models.db.session.add(resource)
        models.db.session.commit()

        assert len(resource.periods) == 1
        assert resource.get_open_period() == period

    def test_get_open_period_with_multiple_open_periods(self):
        resource = fake.get_resource()
        spec = fake.get_instance_spec()

        for _ in range(2):
            period = models.Period(spec=spec)
            period.started_at = datetime.datetime.now()
            resource.periods.append(period)

        models.db.session.add(resource)
        models.db.session.commit()

        with pytest.raises(exceptions.MultipleOpenPeriods) as e:
            resource.get_open_period()

        assert e.value.code == 409
        assert e.value.description == "Multiple open periods"

    def test_get_open_period_with_multiple_periods(self):
        resource = fake.get_resource_with_periods(20)

        period = models.Period(spec=resource.periods[-1].spec)
        period.started_at = datetime.datetime.now()
        resource.periods.append(period)

        models.db.session.add(resource)
        models.db.session.commit()

        assert len(resource.periods) == 21
        assert resource.get_open_period() == period


@pytest.mark.usefixtures("db_session")
class TestInstance:
    def test_is_event_ignored(self):
        event = fake.get_normalized_event()
        assert models.Instance.is_event_ignored(event) == False

    def test_is_event_ignored_for_pending_delete(self):
        event = fake.get_normalized_event()
        event['event_type'] = 'compute.instance.delete.start'
        event['traits']['state'] = 'deleted'
        assert models.Instance.is_event_ignored(event) == True

    def test_is_event_ignored_for_deleted(self):
        event = fake.get_normalized_event()
        event['event_type'] = 'compute.instance.delete.start'
        event['traits']['state'] = 'deleted'
        event['traits']['deleted_at'] = event['generated']
        assert models.Instance.is_event_ignored(event) == False

    def test_get_or_create_has_no_deleted_period(self):
        event = fake.get_normalized_event()
        resource = models.Resource.get_or_create(event)

        assert resource.get_open_period() is not None
        assert len(resource.periods) == 1

        event['event_type'] = 'compute.instance.delete.start'
        event['traits']['state'] = 'deleted'
        event['generated'] += relativedelta(hours=+1)

        with pytest.raises(exceptions.IgnoredEvent) as e:
            models.Resource.get_or_create(event)

        assert resource.get_open_period() is not None
        assert len(resource.periods) == 1

        event['traits']['deleted_at'] = event['generated']
        event['generated'] += relativedelta(seconds=+2)
        resource = models.Resource.get_or_create(event)

        assert resource.get_open_period() is None
        assert len(resource.periods) == 1


@pytest.mark.usefixtures("db_session")
class TestPeriod:
    def test_serialize_without_start(self):
        spec = fake.get_instance_spec()
        period = models.Period(spec=spec)

        resource = fake.get_resource()
        resource.periods.append(period)

        models.db.session.add(resource)
        with pytest.raises(exc.IntegrityError):
            models.db.session.commit()

    def test_serialize_without_ending(self):
        now = datetime.datetime.now()
        started_at = now + relativedelta(hours=-1)

        spec = fake.get_instance_spec()
        period = models.Period(
            started_at=started_at,
            spec=spec
        )

        resource = fake.get_resource()
        resource.periods.append(period)

        with freeze_time(now):
            assert datetime.datetime.now() == now
            assert period.serialize == {
                'started_at': started_at,
                'ended_at': None,
                'seconds': 3600,
                'spec': spec.serialize
            }

    def test_serialize(self):
        started_at = datetime.datetime.now()
        ended_at = started_at + relativedelta(hours=+1)

        spec = fake.get_instance_spec()
        period = models.Period(
            started_at=started_at,
            ended_at=ended_at,
            spec=spec
        )

        resource = fake.get_resource()
        resource.periods.append(period)

        assert period.serialize == {
            'started_at': started_at,
            'ended_at': ended_at,
            'seconds': 3600,
            'spec': spec.serialize
        }


@pytest.mark.usefixtures("db_session")
class TestSpec(GetOrCreateTestMixin):
    MODEL = models.Spec

    def test_from_event(self):
        event = fake.get_normalized_event()
        spec = models.Spec.from_event(event)

        assert spec.instance_type == 'v1-standard-1'
        assert spec.state == 'ACTIVE'

    @mock.patch('flask_sqlalchemy._QueryProperty.__get__')
    def test_query_from_event(self, mock_query_property_getter):
        mock_filter_by = mock_query_property_getter.return_value.filter_by

        event = fake.get_normalized_event()
        query = models.Spec.query_from_event(event)

        mock_filter_by.assert_called_with(
            instance_type='v1-standard-1',
            state='ACTIVE'
        )


@pytest.mark.usefixtures("db_session")
class TestInstanceSpec:
    def test_serialize(self):
        spec = fake.get_instance_spec()

        assert spec.serialize == {
            'instance_type': spec.instance_type,
            'state': spec.state,
        }