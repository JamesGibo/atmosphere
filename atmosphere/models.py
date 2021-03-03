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

"""Models

"""
# pylint: disable=R0903
# pylint: disable=W0223
# pylint: disable=no-member
# pylint: disable=not-an-iterable
from datetime import datetime

from dateutil.relativedelta import relativedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc
from sqlalchemy.types import TypeDecorator
from sqlalchemy import or_

from atmosphere import exceptions

session_options = {
    'autocommit': False
}

db = SQLAlchemy(session_options=session_options)
migrate = Migrate()


MONTH_START = relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_model_type_from_event(event):
    """get_model_type_from_event"""
    if event.startswith('compute.instance'):
        return Instance, InstanceSpec
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


class GetOrCreateMixin:
    """GetOrCreateMixin"""

    @classmethod
    def get_or_create(cls, event):
        """get_or_create"""
        query = cls.query_from_event(event)
        new_instance = cls.from_event(event)

        db_instance = query.first()
        if db_instance is None:
            db_instance = new_instance

            db.session.begin(nested=True)
            try:
                db.session.add(db_instance)
                db.session.commit()
            except (exc.IntegrityError, orm_exc.FlushError):
                db.session.rollback()
                db_instance = query.one()

        return db_instance


class Resource(db.Model, GetOrCreateMixin):
    """Resource"""

    uuid = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.String(32), nullable=False)
    project = db.Column(db.String(32), nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    periods = db.relationship('Period', backref='resource', lazy='joined')

    __mapper_args__ = {
        'polymorphic_on': type
    }

    @classmethod
    def get_all_by_time_range(cls, start, end, project=None):
        """Get all resources given a specific period."""
        query = cls.query.join(Period).filter(
            # Resources must have started before the end
            Period.started_at <= end,
            # Resources must be still active or ended after start
            or_(
                Period.ended_at >= start,
                Period.ended_at.is_(None)
            ),
        )

        if project is not None:
            query = query.filter(Resource.project == project)

        resources = query.all()
        for resource in resources:
            for period in resource.periods:
                db.session.expunge(period)
                if period.started_at <= start:
                    period.started_at = start
                if period.ended_at is None or period.ended_at >= end:
                    period.ended_at = end
            resource.periods = [p for p in resource.periods if p.seconds != 0]

        return resources

    @classmethod
    def from_event(cls, event):
        """from_event"""
        cls, _ = get_model_type_from_event(event['event_type'])

        return cls(
            uuid=event['traits']['resource_id'],
            project=event['traits']['project_id'],
            updated_at=event['generated'],
        )

    @classmethod
    def query_from_event(cls, event):
        """query_from_event"""
        cls, _ = get_model_type_from_event(event['event_type'])

        return cls.query.filter_by(
            uuid=event['traits']['resource_id'],
            project=event['traits']['project_id'],
        ).with_for_update()

    @classmethod
    def get_or_create(cls, event):
        """get_or_create"""
        resource = super(Resource, cls).get_or_create(event)

        # If the last update is newer than our last update, we assume that
        # another event has been processed that is newer (so we should ignore
        # this one).
        time = event['generated']
        if resource.updated_at is not None and resource.updated_at > time:
            raise exceptions.EventTooOld()

        # Update the last updated_at time now so any older events get rejected
        db.session.commit()

        # Check if we should ignore event
        if resource.__class__.is_event_ignored(event):
            raise exceptions.IgnoredEvent

        # Retrieve spec for this event
        spec = Spec.get_or_create(event)

        # No existing period, start our first period.
        if len(resource.periods) == 0:
            resource.periods.append(Period(
                started_at=event['traits'].get('created_at') or
                event['traits'].get('launched_at'),
                spec=spec
            ))

        # Grab the current open period to manipulate it
        period = resource.get_open_period()

        # If we don't have an open period, there's nothing to do.
        if period is None:
            raise exceptions.EventTooOld()

        # If we're deleted, then we close the current period.
        if 'deleted_at' in event['traits']:
            period.ended_at = event['traits']['deleted_at']
        elif period.spec != spec:
            period.ended_at = event['generated']

            resource.periods.append(Period(
                started_at=event['generated'],
                spec=spec,
            ))

        # Bump updated_at to event time (in order to avoid conflicts)
        resource.updated_at = time
        db.session.commit()

        return resource

    def get_open_period(self):
        """get_open_period"""
        open_periods = list(filter(lambda p: p.ended_at is None, self.periods))
        if len(open_periods) > 1:
            raise exceptions.MultipleOpenPeriods
        if len(open_periods) == 0:
            return None
        return open_periods[0]

    @property
    def serialize(self):
        """Return object data in easily serializable format"""

        return {
            'uuid': self.uuid,
            'type': self.type,
            'project': self.project,
            'updated_at': self.updated_at,
            'periods': [p.serialize for p in self.periods],
            }


class Instance(Resource):
    """Instance"""

    __mapper_args__ = {
        'polymorphic_identity': 'OS::Nova::Server'
    }

    @classmethod
    def is_event_ignored(cls, event):
        """is_event_ignored"""
        vm_state_is_deleted = (event['traits']['state'] == 'deleted')
        no_deleted_at = ('deleted_at' not in event['traits'])

        if vm_state_is_deleted and no_deleted_at:
            return True

        # Check if event is missing both created_at and launched_at traits
        no_created_at = ('created_at' not in event['traits'])
        no_launched_at = ('launched_at' not in event['traits'])
        if no_created_at and no_launched_at:
            return True

        return False


class BigIntegerDateTime(TypeDecorator):
    """BigIntegerDateTime"""

    impl = db.BigInteger

    def process_bind_param(self, value, _):
        """process_bind_param"""
        if value is None:
            return None
        assert isinstance(value, datetime)
        return value.timestamp() * 1000

    def process_result_value(self, value, _):
        """process_result_value"""
        if value is None:
            return None
        return datetime.fromtimestamp(value / 1000)


class Period(db.Model):
    """Period"""

    id = db.Column(db.Integer, primary_key=True)
    resource_uuid = db.Column(db.String(36), db.ForeignKey('resource.uuid'),
                              nullable=False)
    started_at = db.Column(BigIntegerDateTime, nullable=False, index=True)
    ended_at = db.Column(BigIntegerDateTime, index=True)

    spec_id = db.Column(db.Integer, db.ForeignKey('spec.id'), nullable=False)
    spec = db.relationship("Spec", lazy='joined')

    @property
    def seconds(self):
        """seconds"""
        ended_at = self.ended_at
        if ended_at is None:
            ended_at = datetime.now()
        return (ended_at - self.started_at).total_seconds()

    @property
    def serialize(self):
        """Return object data in easily serializable format"""

        return {
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'seconds': self.seconds,
            'spec': self.spec.serialize,
            }


class Spec(db.Model, GetOrCreateMixin):
    """Spec"""

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32))

    __mapper_args__ = {
        'polymorphic_on': type
    }

    @classmethod
    def from_event(cls, event):
        """from_event"""
        _, cls = get_model_type_from_event(event['event_type'])
        spec = {c.name: event['traits'][c.name]
                for c in cls.__table__.columns if c.name != 'id'}

        return cls(**spec)

    @classmethod
    def query_from_event(cls, event):
        """query_from_event"""
        _, cls = get_model_type_from_event(event['event_type'])
        spec = {c.name: event['traits'][c.name]
                for c in cls.__table__.columns if c.name != 'id'}

        return cls.query.filter_by(**spec)


class InstanceSpec(Spec):
    """InstanceSpec"""

    id = db.Column(db.Integer, db.ForeignKey('spec.id'), primary_key=True)
    instance_type = db.Column(db.String(255))
    state = db.Column(db.String(255))

    __table_args__ = (
        db.UniqueConstraint('instance_type', 'state'),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'OS::Nova::Server',
    }

    @property
    def serialize(self):
        """Return object data in easily serializable format"""

        return {
            'instance_type': self.instance_type,
            'state': self.state,
            }
