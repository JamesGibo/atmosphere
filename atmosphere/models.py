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

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc
from dateutil.relativedelta import relativedelta
from sqlalchemy.types import TypeDecorator

from atmosphere import exceptions
from atmosphere import utils

db = SQLAlchemy()
migrate = Migrate()


MONTH_START = relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)


class GetOrCreateMixin:
    @classmethod
    def get_or_create(self, event):
        query = self.query_from_event(event)
        new_instance = self.from_event(event)

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
    uuid = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.String(32), nullable=False)
    project = db.Column(db.String(32), nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    periods = db.relationship('Period', backref='resource', lazy='joined')

    __mapper_args__ = {
        'polymorphic_on': type
    }

    @classmethod
    def from_event(self, event):
        cls, _ = utils.get_model_type_from_event(event['event_type'])

        return cls(
            uuid=event['traits']['resource_id'],
            project=event['traits']['project_id'],
            updated_at=event['generated'],
        )

    @classmethod
    def query_from_event(self, event):
        cls, _ = utils.get_model_type_from_event(event['event_type'])

        return cls.query.filter_by(
            uuid=event['traits']['resource_id'],
            project=event['traits']['project_id'],
        ).with_for_update()

    @classmethod
    def get_or_create(self, event):
        resource = super(Resource, self).get_or_create(event)

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
                started_at=event['traits']['created_at'],
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
    __mapper_args__ = {
        'polymorphic_identity': 'OS::Nova::Server'
    }

    @classmethod
    def is_event_ignored(self, event):
        vm_state_is_deleted = (event['traits']['state'] == 'deleted')
        no_deleted_at = ('deleted_at' not in event['traits'])

        if vm_state_is_deleted and no_deleted_at:
            return True

        return False


class BigIntegerDateTime(TypeDecorator):
    impl = db.BigInteger

    def process_bind_param(self, value, _):
        if value is None:
            return None
        assert isinstance(value, datetime)
        return value.timestamp() * 1000

    def process_result_value(self, value, _):
        if value is None:
            return None
        return datetime.fromtimestamp(value / 1000)


class Period(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_uuid = db.Column(db.String(36), db.ForeignKey('resource.uuid'),
                              nullable=False)
    started_at = db.Column(BigIntegerDateTime, nullable=False, index=True)
    ended_at = db.Column(BigIntegerDateTime, index=True)

    spec_id = db.Column(db.Integer, db.ForeignKey('spec.id'), nullable=False)
    spec = db.relationship("Spec")

    @property
    def seconds(self):
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
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(32))

    __mapper_args__ = {
        'polymorphic_on': type
    }

    @classmethod
    def from_event(self, event):
        _, cls = utils.get_model_type_from_event(event['event_type'])
        spec = {c.name: event['traits'][c.name]
                for c in cls.__table__.columns if c.name != 'id'}

        return cls(**spec)

    @classmethod
    def query_from_event(self, event):
        _, cls = utils.get_model_type_from_event(event['event_type'])
        spec = {c.name: event['traits'][c.name]
                for c in cls.__table__.columns if c.name != 'id'}

        return cls.query.filter_by(**spec)


class InstanceSpec(Spec):
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
