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

import pytest

from atmosphere.tests.unit import fake
from atmosphere import exceptions
from atmosphere import models
from atmosphere import utils


class TestNormalizeEvent:
    def test_normalize_event(self):
        event = fake.get_event()
        event_expected = fake.get_event()
        event_expected.update({
            "generated": datetime.datetime(2020, 6, 7, 1, 42, 54, 736337),
            "traits": {
                "service": "compute.devstack",
                "request_id": "req-cc707e71-8ea7-4646-afb6-65a8d1023c1a",
                "created_at": datetime.datetime(2020, 6, 7, 1, 42, 52),
                "project_id": "fake-project",
                "resource_id": "fake-uuid",
                "instance_type": "v1-standard-1",
                "state": "ACTIVE",
            }
        })

        assert utils.normalize_event(event) == event_expected


class TestModelTypeDetection:
    def test_compute_instance(self):
        assert utils.get_model_type_from_event('compute.instance.exists') == \
            (models.Instance, models.InstanceSpec)

    def test_ignored_resource(self, ignored_event):
        with pytest.raises(exceptions.IgnoredEvent) as e:
            utils.get_model_type_from_event(ignored_event)

        assert e.value.description == "Ignored event type"

    def test_unknown_resource(self):
        with pytest.raises(exceptions.UnsupportedEventType) as e:
            utils.get_model_type_from_event('foobar')

        assert e.value.code == 400
        assert e.value.description == "Unsupported event type"
