#!/usr/bin/env bash
# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# 
# modified by v.kozlov @2018-07-18 
# to include jupyterCONF environment check
######

if [[ ! -v jupyterOPTS ]]; then
    jupyterOPTS=""
fi

# Check if jupyterCONF environment is specified (can be passed to docker via "--env jupyterCONF=value")
# If so, check for:
#    jupyter_config_user.py - Jupyter config file defined by user, e.g. with pre-configured password
#    jupyterSSL.key   - private key file for usage with SSL/TLS
#    jupyterSSL.pem   - the full path to an SSL/TLS certificate file
#
# Idea: local directory at host machine with those files is mounted to docker container, e.g.
#     --volume=host_dir:dir_in_container --env jupyterCONF=dir_in_container
# such that SSL connection is established and user-defined jupyter config is used

if [[ -v jupyterCONF ]]; then
    [[ -f $jupyterCONF/jupyter_config_user.py ]] && jConfig="$jupyterCONF/jupyter_config_user.py" && jupyterOPTS=$jupyterOPTS" --config=u'$jConfig'"
    [[ -f $jupyterCONF/jupyterSSL.key ]] && jKeyfile="$jupyterCONF/jupyterSSL.key" && jupyterOPTS=$jupyterOPTS" --keyfile=u'$jKeyfile'"
    [[ -f $jupyterCONF/jupyterSSL.pem ]] && jCertfile="$jupyterCONF/jupyterSSL.pem" && jupyterOPTS=$jupyterOPTS" --certfile=u'$jCertfile'"
fi


jupyter notebook $jupyterOPTS "$@"
