#!/usr/bin/env python

from __future__ import print_function

"""
site.pp generator
"""

import os
import sys
import json
import inflect
import argparse
from configparser import SafeConfigParser

debug = False
write_to = sys.stdout

def eprint(*args, **kwargs):
    global debug
    if debug:
        print(*args, file=sys.stderr, **kwargs)

def print_resource(resource_name, resource_alias, strategy='deep'):
    global debug, write_to

    # lookup( <NAME>, [<VALUE TYPE>], [<MERGE BEHAVIOR>], [<DEFAULT VALUE>] )
    print("", file=write_to)
    # print("$resource_alias = lookup('"+resource_alias+"', undef, '"+strategy+"', {})", file=write_to)
    print("$"+resource_alias+" = lookup("+resource_alias+", Hash, "+strategy+", {})", file=write_to)
    # create_resources(postgresql::schema, $postgresschemas)
    print("create_resources("+resource_name+", $"+resource_alias+")", file=write_to)


def generatesitepp(config_file, write_sitepp_to=sys.stdout):
    global debug, write_to

    write_to=write_sitepp_to

    config = SafeConfigParser()
    config.read(config_file)

    try:
        debug = config.getboolean('sitegen', 'debug')
    except:
        debug = False

    try:
        resource_file = config.get('sitegen', 'resource-file').strip('"').strip("'").strip()
    except:
        resource_file = "./siteppgen/resource.list"

    try:
        resource_hash = json.loads(config.get('sitegen','resource-hash'))
    except:
        resource_hash = {}

    try:
        deep_include_classes = json.loads(config.get('sitegen','deep-include-classes'))
    except:
        deep_include_classes = []

    # resource_hash
    for resource_alias in resource_hash:
        # print resource hash
        print_resource(resource_hash[resource_alias], resource_alias)

    # resource_file
    if not os.path.isfile(resource_file):
        eprint("WARNING: resource-file ("+resource_file+") not found, ignoring resources")

    with open(resource_file) as resource_file_handler:
       resource_name = resource_file_handler.readline().rstrip(os.linesep).strip('"').strip("'").strip()
       while resource_name:
           resource_alias = resource_name.replace(':','').strip()+"s"
           print_resource(resource_name, resource_alias)

           p = inflect.engine()
           plural_resource_alias = p.plural(resource_name.replace(':','').strip())

           if plural_resource_alias != resource_alias:
               print_resource(resource_name, plural_resource_alias)


           resource_name = resource_file_handler.readline().rstrip(os.linesep).strip('"').strip("'").strip()

    for resource_alias in config.sections():
        if resource_alias!="sitegen":
            try:
                merge_strategy = config.get(resource_alias, 'merge-strategy').strip('"').strip("'").strip()
            except:
                merge_strategy = 'deep'

            try:
                resource_name = config.get(resource_alias, 'resource-name').strip('"').strip("'").strip()
                print_resource(resource_name, resource_alias, merge_strategy)
            except:
                eprint("WARNING: skipping "+resource_alias+": resource-name not found")

    # lookup('classes', Array[String], 'deep').include
    for deep_include_class in deep_include_classes:
        print("", file=write_to)
        print("lookup('"+deep_include_class+"', Array[String], 'deep').include", file=write_to)


if __name__ == '__main__':
    try:
        config_file = sys.argv[1]
    except IndexError:
        config_file = './siteppgen.config'
    generatesitepp(config_file=config_file)
