# Copyright (c) 2020 VEXXHOST, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM docker.io/opendevorg/python-builder as builder
COPY . /tmp/src
RUN assemble

FROM docker.io/opendevorg/uwsgi-base AS atmosphere
COPY --from=builder /output/ /output
RUN rm -rfv /output/packages.txt && \
    /output/install-from-bindep
EXPOSE 8080
ENV FLASK_APP=atmosphere.app \
    UWSGI_HTTP_SOCKET=:8080

FROM atmosphere AS atmosphere-ingress
ENV UWSGI_WSGI_FILE=/usr/local/bin/atmosphere-ingress-wsgi