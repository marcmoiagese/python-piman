#!/usr/bin/env python

from __future__ import print_function

"""
hiera.yaml generator
"""

import os
import sys
import json
import argparse
import collections
from configparser import RawConfigParser

debug = False
write_to = sys.stdout

def eprint(*args, **kwargs):
    global debug
    if debug:
        print(*args, file=sys.stderr, **kwargs)

def mkdir_gitkeep(dirname):
    os.makedirs(name=dirname, exist_ok=True)
    gitkeep = open(dirname+"/.gitkeep","w+")
    gitkeep.close()

def print_hierarchy_item(item_name, globs, auth_string, write_to=sys.stdout):
    print('  - name: "'+item_name+'"', file=write_to)
    print('    globs:', file=write_to)
    for glob in globs:
        print('      - "' + auth_string + glob+'/*.yaml"', file=write_to)
        print('      - "' + auth_string + glob+'.yaml"', file=write_to)
    print('', file=write_to)

def generatehieradataskel(config_file, hieradata_base_dir='', create_skel_auth_strings=[]):
    global debug

    config = RawConfigParser()
    config.read(config_file)

    try:
        debug = config.getboolean('hieragen', 'debug')
    except:
        debug = False

    try:
        unauth_common_area = config.get('hieragen','unauth-common-area')
    except:
        unauth_common_area = True

    if unauth_common_area:
        mkdir_gitkeep(hieradata_base_dir+'/common')

    for project_id in create_skel_auth_strings:
        if debug:
            eprint("SKEL for "+project_id+": "+hieradata_base_dir+'/'+project_id)
        for dir_name in [ '/env', '/hierarchy', '/type', '/servergroup', '/node', '/config-catalog' ]:
            mkdir_gitkeep(hieradata_base_dir+'/'+project_id+'/'+dir_name)

def writehierayaml(write_to=sys.stdout, auth_string='', hierarchy={}, include_override=True, unauth_common_area=True, puppet_agent_common_area=True):
    print('---', file=write_to)
    print('version: 5', file=write_to)
    print('', file=write_to)
    print('defaults:', file=write_to)
    print('  datadir: hieradata', file=write_to)
    print('  data_hash: yaml_data', file=write_to)
    print('', file=write_to)
    print('hierarchy:', file=write_to)
    if include_override:
        print('  - name: "override"', file=write_to)
        print('    globs:', file=write_to)
        print('      - "override/*.yaml"', file=write_to)
        print('      - "override.yaml"', file=write_to)
        print('', file=write_to)
    
    for key, value in hierarchy.items():
        print_hierarchy_item(key, value, auth_string, write_to)

    if unauth_common_area:
        print('  - name: "common os release"', file=write_to)
        print('    globs:', file=write_to)
        print('      - "common-%{::osfamily}-%{::operatingsystemmajrelease}/*.yaml"', file=write_to)
        print('      - "common-%{::osfamily}-%{::operatingsystemmajrelease}.yaml"', file=write_to)
        print('', file=write_to)
        print('  - name: "common os family"', file=write_to)
        print('    globs:', file=write_to)
        print('      - "common-%{::osfamily}/*.yaml"', file=write_to)
        print('      - "common-%{::osfamily}.yaml"', file=write_to)
        print('', file=write_to)
        print('  - name: "common"', file=write_to)
        print('    globs:', file=write_to)
        print('      - "common/*.yaml"', file=write_to)
        print('      - "common.yaml"', file=write_to)
    if puppet_agent_common_area:
        print('', file=write_to)
        print('  - name: "puppet agent config"', file=write_to)
        print('    globs:', file=write_to)
        print('      - "puppet-agent-config/*.yaml"', file=write_to)
        print('      - "puppet-agent-config.yaml"', file=write_to)

def generatehierayaml(config_file, write_hierayaml_to=sys.stdout, hieradata_base_dir='', puppet_fqdn='', puppet_port=None, create_skel_auth_strings=[]):
    global debug, write_to

    write_to=write_hierayaml_to

    config = RawConfigParser()
    config.read(config_file)

    try:
        auth_facts = json.loads(config.get('hieragen','auth-facts'))
    except:
        auth_facts = []

    try:
        auth_facts_separator = json.loads(config.get('hieragen','auth-facts-separator'))
    except:
        auth_facts_separator = '_'

    try:
        include_override = config.get('hieragen','include-override')
    except:
        include_override = True

    try:
        unauth_common_area = config.get('hieragen','unauth-common-area')
    except:
        unauth_common_area = True

    try:
        puppet_agent_common_area = config.get('hieragen','puppet-agent-common-area')
    except:
        puppet_agent_common_area = True

    try:
        debug = config.getboolean('hieragen', 'debug')
    except:
        debug = False

    if debug:
        eprint('auth_facts:'+str(auth_facts))

    formated_auth_facts = []
    for fact in auth_facts:
        formated_auth_facts.append("%{::"+fact+"}")

    auth_string = auth_facts_separator.join(formated_auth_facts)+'/'

    if debug:
        eprint('auth_string:'+auth_string)

    if debug and hieradata_base_dir:
        eprint('hieradata_base_dir: '+str(hieradata_base_dir))

    hierarchy = collections.OrderedDict()
    for instance in config.sections():
        if instance!='hieragen':
            globs = []
            for (item, value) in config.items(instance):
                if value!='0':
                    glob=item+':'+value
                else:
                    glob=item
                globs.append(glob)
            hierarchy[instance]=globs

    writehierayaml(write_to, auth_string, hierarchy, include_override, unauth_common_area, puppet_agent_common_area)

    if hieradata_base_dir:
        mkdir_gitkeep(hieradata_base_dir)

        if puppet_agent_common_area and puppet_fqdn:
            if not os.path.isfile(hieradata_base_dir+"/puppet-agent-config.yaml"):
                puppet_agent_config = open(hieradata_base_dir+"/puppet-agent-config.yaml","w+")
                puppet_agent_config.write("---\n")
                puppet_agent_config.write("classes:\n")
                puppet_agent_config.write("  - puppet::agent\n")
                puppet_agent_config.write("puppet::agent::puppetmaster: "+puppet_fqdn+"\n")
                if puppet_port:
                    puppet_agent_config.write("puppet::agent::puppetmasterport: "+str(puppet_port)+"\n")
                puppet_agent_config.close()

        generatehieradataskel(config_file, hieradata_base_dir, create_skel_auth_strings)


if __name__ == '__main__':
    try:
        config_file = sys.argv[1]
    except IndexError:
        config_file = './hieragen.config'
    generatehierayaml(config_file=config_file)
