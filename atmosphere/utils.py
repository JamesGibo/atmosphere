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

from ceilometer.event import models as ceilometer_models
from dateutil import parser

from atmosphere import exceptions
from atmosphere import models


def normalize_event(event):
    event['generated'] = parser.parse(event['generated'])
    event['traits'] = {
        k: ceilometer_models.Trait.convert_value(t, v)
        for (k, t, v) in event['traits']
    }

    return event


def get_model_type_from_event(event):
    if event.startswith('compute.instance'):
        return models.Instance, models.InstanceSpec
    if event.startswith('aggregate.'):
        raise exceptions.IgnoredEvent
    if event.startswith('compute_task.'):
        raise exceptions.IgnoredEvent
    if event.startswith('compute.'):
        raise exceptions.IgnoredEvent
    if event.startswith('flavor.'):
        raise exceptions.IgnoredEvent
    if event.startswith('keypair.'):
        raise exceptions.IgnoredEvent
    if event.startswith('libvirt.'):
        raise exceptions.IgnoredEvent
    if event.startswith('metrics.'):
        raise exceptions.IgnoredEvent
    if event.startswith('scheduler.'):
        raise exceptions.IgnoredEvent
    if event.startswith('server_group.'):
        raise exceptions.IgnoredEvent
    if event.startswith('service.'):
        raise exceptions.IgnoredEvent
    if event == 'volume.usage':
        raise exceptions.IgnoredEvent

    raise exceptions.UnsupportedEventType


