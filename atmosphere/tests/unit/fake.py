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

from dateutil.relativedelta import relativedelta

from atmosphere import models
from atmosphere import utils


def get_instance_event(resource_id='fake-uuid', event_type='compute.instance.exists'):
    return dict({
        'generated': '2020-06-07T01:42:54.736337',
        'event_type': event_type,
        'traits': [
            ["service", 1, "compute.devstack"],
            ["request_id", 1, "req-cc707e71-8ea7-4646-afb6-65a8d1023c1a"],
            ["created_at", 4, "2020-06-07T01:42:52"],
            ["resource_id", 1, resource_id],
            ["project_id", 1, "fake-project"],
            ["instance_type", 1, "v1-standard-1"],
            ["state", 1, "ACTIVE"],
        ]
    })


def get_volume_event(resource_id='fake-uuid', event_type='volume.exists'):
    return dict({
        'generated': '2020-06-07T01:42:54.736337',
        'event_type': event_type,
        'traits': [
            ["service", 1, "volume.ironic-devstack"],
            ["request_id", 1, "req-66a05c73-964e-4d12-a0c3-7d3b0d5801ce"],
            ["project_id", 1, "a1da863b589642558b7a87f09840a565"],
            ["user_id", 1, "a6db2097a75a4cf3b3b4336108017aae"],
            ["tenant_id", 1, "a1da863b589642558b7a87f09840a565"],
            ["resource_id", 1, "3c1e0499-7621-496c-bab4-59a7053f8b59"],
            ["volume_type", 1, "7d233c12-d346-4948-8901-7afd5c5dd590"],
            ["volume_size", 2, 1],
            ["state", 1, "available"],
            ["created_at", 4, "2021-03-26T00:36:28"],
        ]
    })


def get_normalized_instance_event():
    event = get_instance_event()
    return utils.normalize_event(event)


def get_normalized_volume_event():
    event = get_volume_event()
    return utils.normalize_event(event)


def get_resource(type='OS::Nova::Server'):
    return models.Resource(uuid='fake-uuid', type=type,
                           project='fake-project',
                           updated_at=datetime.datetime.now())


def get_instance_spec(**kwargs):
    if not kwargs:
        kwargs = {'instance_type': 'v2-standard-1', 'state': 'ACTIVE'}
    return models.InstanceSpec(**kwargs)


def get_volume_spec(**kwargs):
    if not kwargs:
        kwargs = {
            'volume_type': '7d233c12-d346-4948-8901-7afd5c5dd590',
            'volume_size': 3,
            'state': 'available'
        }
    return models.VolumeSpec(**kwargs)


def get_resource_with_periods(number):
    resource = get_resource()

    spec = get_instance_spec()
    models.db.session.add(spec)

    for i in range(number):
        period = models.Period(spec=spec)
        period.started_at = datetime.datetime.now() + relativedelta(hour=+i)
        period.ended_at = period.started_at + relativedelta(hour=+1)
        resource.periods.append(period)

    return resource
