#!/usr/bin/env python

from __future__ import print_function

"""
Puppet Instance MANager
"""

import sh
import os
import sys
import stat
import json
import glob
import pfgen
import pickle
import string
import random
import getopt
import argparse
import datetime
import hieragen
import siteppgen
from io import StringIO
from pathlib import Path
from github import Github
from configparser import SafeConfigParser
from distutils.version import LooseVersion

def eprint(*args, **kwargs):
    ''' print to stderr'''
    print(*args, file=sys.stderr, **kwargs)

def save_puppet_details_to_file(fqdn, puppetmaster_port, puppetboard_port, projects_authstrings, filename):
    dict = {'fqdn': fqdn, 'puppetmaster_port': puppetmaster_port, 'puppetboard_port': puppetboard_port, 'projects_authstrings': projects_authstrings}
    file = open(filename, 'wb')
    pickle.dump(dict, file)
    file.close()

def load_puppet_details_to_file(filename):
    file = open(filename, 'rb')
    return pickle.load(file)

def load_proc_net_tcp():
    ''' Read the table of tcp connections & remove header  '''
    with open('/proc/net/tcp','r') as f:
        content = f.readlines()
        content.pop(0)
    return content

def _hex2dec(s):
    return str(int(s,16))

def _ip(s):
    ip = [(_hex2dec(s[6:8])),(_hex2dec(s[4:6])),(_hex2dec(s[2:4])),(_hex2dec(s[0:2]))]
    return '.'.join(ip)

def _convert_ip_port(array):
    host,port = array.split(':')
    return _ip(host),_hex2dec(port)

def _remove_empty(array):
    return [x for x in array if x !='']

def get_free_tcp_port(base_port):

    candidate_port = base_port

    proc_net_tcp = load_proc_net_tcp()
    tcp_listen_ports = []
    for line in proc_net_tcp:
        line_array = _remove_empty(line.split(' '))
        l_host,l_port = _convert_ip_port(line_array[1]) # Convert ipaddress and port from hex to decimal.

        # '0A':'LISTEN',
        if(line_array[3]=='0A'):
            tcp_listen_ports.append(l_port)

    # if debug:
    #     print(str(tcp_listen_ports))

    found_port=False
    while not found_port:
        for listen_port in tcp_listen_ports:
            # if debug:
            #     print(str(listen_port)+' vs '+candidate_port)
            if listen_port == candidate_port:
                candidate_port=candidate_port+1
                found_port=False
                break
        found_port=True

    return candidate_port

def random_string_lowercase_digits(size=10):
    lowercase_and_digits = string.ascii_lowercase + string.digits
    return ''.join(random.choice(lowercase_and_digits) for i in range(size))

def showJelp(msg):
    print("Usage:")
    print("   [-c|--config] <config file>")
    print("   [-h|--help]  -- show this message")
    print("");
    sys.exit(msg)

if __name__ == '__main__':

    config_file = './piman.config'
    auth_strings = []

    # parse opts
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'hlc:', [
                                                                    'help'
                                                                    'config=',
                                                                 ])
    except Exception as e:
        showJelp(str(e))


    for opt, arg in options:
        if opt in ('-h', '--help'):
            showJelp("unknow option")
        elif opt in ('-c', '--config'):
            config_file = arg
        else:
            showJelp("unknow option")

    config = SafeConfigParser()
    config.read(config_file)

    #
    # config comuna
    #

    try:
        base_dir = config.get('piman', 'base-dir').strip('"').strip("'").strip()
    except:
        try:
            base_dir = config.get('piman', 'instance-dir').strip('"').strip("'").strip()
        except:
            sys.exit("ERROR: base-dir is mandatory")

    try:
        instance_template = config.get('piman', 'instance-template').strip('"').strip("'").strip()
    except:
        sys.exit("ERROR: instance-template is mandatory")

    try:
        puppet_fqdn = config.get('piman', 'puppet-fqdn').strip('"').strip("'").strip()
    except:
        sys.exit("ERROR: puppet-fqdn is mandatory")

    try:
        debug = config.getboolean('piman', 'debug')
    except:
        debug = False

    try:
        base_port = config.get('piman', 'base-port')
    except:
        base_port = 8240

    try:
        config_dir = config.get('piman', 'config-dir')
    except:
        config_dir = '.'

    try:
        pfgen_config = config.get('piman', 'pfgen-config')
    except:
        pfgen_config = config_dir+'/pfgen.config'

    try:
        skip_pfgen = config.getboolean('piman', 'skip-pfgen')
    except:
        skip_pfgen = False

    try:
        refresh_hierayaml = config.getboolean('piman', 'refresh-hierayaml')
    except:
        refresh_hierayaml = False

    try:
        hierayaml_config = config.get('piman', 'hierayaml-config')
    except:
        hierayaml_config = config_dir+'/hieragen.config'

    try:
        sitepp_config = config.get('piman', 'sitepp-config')
    except:
        sitepp_config = config_dir+'/siteppgen.config'

    try:
        enable_puppetboard = config.getboolean('piman', 'enable-puppetboard')
    except:
        enable_puppetboard = True

    try:
        bind_ip = config.get('piman','bind-ip').strip('"').strip("'").strip()+':'
    except:
        bind_ip = ''

    #
    # instances puppet
    #

    for instance in config.sections():
        if instance!="piman":

            if debug:
                print("= INSTANCE: "+instance)

            try:
                instance_config_remote = config.get(instance, 'config').strip('"').strip("'").strip()
            except:
                eprint("ERROR INSTANCE "+instance+": config is mandatory")

            try:
                instance_ssl_remote = config.get(instance, 'ssl').strip('"').strip("'").strip()
            except:
                eprint("ERROR INSTANCE "+instance+": ssl is mandatory")

            try:
                instance_instance_remote = config.get(instance, 'instance').strip('"').strip("'").strip()
            except:
                eprint("ERROR INSTANCE "+instance+": instance is mandatory")

            try:
                instance_files_remote = config.get(instance, 'files').strip('"').strip("'").strip()
            except:
                eprint("ERROR INSTANCE "+instance+": files is mandatory")

            try:
                projects = json.loads(config.get(instance,'projects'))
            except:
                projects = []

            try:
                append_random_string = config.getboolean(instance, 'projects-append-randomstring')
            except:
                append_random_string = True

            try:
                bind_ip = config.get(instance,'bind-ip').strip('"').strip("'").strip()+':'
            except:
                try:
                    bind_ip = config.get('piman','bind-ip').strip('"').strip("'").strip()+':'
                except:
                    bind_ip = ''

            try:
                add_default_network = config.getboolean(instance, 'add-default-network')
            except:
                add_default_network = False

            try:
                author_email = config.get(instance, 'author-email').strip('"').strip("'").strip()
            except:
                author_email="autocommit@systemadmin.es"

            try:
                author_name = config.get(instance, 'author-name').strip('"').strip("'").strip()
            except:
                author_name="Dr. Auto Commit"

            try:
                puppet_fqdn = config.get(instance, 'puppet-fqdn').strip('"').strip("'").strip()
            except:
                puppet_fqdn = config.get('piman', 'puppet-fqdn').strip('"').strip("'").strip()

            try:
                enable_puppetboard = config.getboolean(instance, 'enable-puppetboard')
            except:
                try:
                    enable_puppetboard = config.getboolean('piman', 'enable-puppetboard')
                except:
                    enable_puppetboard = True

            try:
                skip_pfgen = config.getboolean(instance, 'skip-pfgen')
            except:
                try:
                    skip_pfgen = config.getboolean('piman', 'skip-pfgen')
                except:
                    skip_pfgen = False

            try:
                refresh_hierayaml = config.getboolean(instance, 'refresh-hierayaml')
            except:
                try:
                    refresh_hierayaml = config.getboolean('piman', 'refresh-hierayaml')
                except:
                    refresh_hierayaml = False

            #
            # instance repo
            #

            instance_repo_path = base_dir+'/'+instance+'/instance'
            os.makedirs(name=instance_repo_path, exist_ok=True)

            if debug:
                print("DEBUG: instance repo path: "+instance_repo_path)

            if os.path.isdir(instance_repo_path+'/.git'):
                # repo ja colonat
                if debug:
                    print(instance+': instance repo ja clonat: '+instance_repo_path)

                # update repo desde remote
                git_instance_repo = sh.git.bake(_cwd=instance_repo_path, _env={"EMAIL": author_email,"GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email, "GIT_SSH_COMMAND": "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"})
                git_instance_repo.pull('origin', 'master')

                saved_config = load_puppet_details_to_file(instance_repo_path+'/.piman.data')
                puppet_master_port = saved_config['puppetmaster_port']
                puppet_board_port = saved_config['puppetboard_port']
                projects_authstrings = saved_config['projects_authstrings']

                for project in projects:
                    found_project=False
                    for project_authstring in projects_authstrings:
                        if project_authstring.startswith(project):
                            found_project=True
                            break
                    if not found_project:
                        project_auth_string = project+'_'+random_string_lowercase_digits()
                        projects_authstrings.append(project_auth_string)

                save_puppet_details_to_file(puppet_fqdn, puppet_master_port, puppet_board_port, projects_authstrings, instance_repo_path+'/.piman.data')

                sh.sed('s/^# docker-puppetmaster5/# '+instance+'/','-i', instance_repo_path+'/README.md')
            else:
                #clonar repo, importar desde template
                sh.git.clone(instance_instance_remote, instance_repo_path, _env={"EMAIL": author_email, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email, "GIT_SSH_COMMAND": "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"})

                # TODO: check si el repo remot ja conté dades

                git_instance_repo = sh.git.bake(_cwd=instance_repo_path, _env={"EMAIL": author_email, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email, "GIT_SSH_COMMAND": "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"})
                git_instance_repo.remote.add('template', instance_template)
                git_instance_repo.pull('template', 'master')

                sh.bash(instance_repo_path+'/update.utils.sh', _cwd=instance_repo_path)

                sh.cp(glob.glob(str(Path.home())+'/.ssh/id*a'), instance_repo_path+'/ssh')

                sh.sed('s/^# docker-puppetmaster5/# '+instance+'/','-i', instance_repo_path+'/README.md')

                gitignore = open(instance_repo_path+"/.gitignore","w+")
                gitignore.write("*~\n")
                gitignore.write("*swp\n")
                gitignore.write("ssh/id_*\n")
                gitignore.write("utils/puppet-masterless\n")
                gitignore.write("utils/autocommit\n")
                gitignore.write("puppetboard/\n")
                gitignore.close()

                projects_authstrings=[]
                for project in projects:
                    project_auth_string = project+'_'+random_string_lowercase_digits()
                    projects_authstrings.append(project_auth_string)
                    if debug:
                        print("for project "+project+" auth string: "+project_auth_string)

                try:
                    puppet_master_port = config.get(instance, 'puppet-master-port').strip('"').strip("'").strip()
                except:
                    puppet_master_port = None

                try:
                    puppet_board_port = config.get(instance, 'puppet-board-port').strip('"').strip("'").strip()
                except:
                    puppet_board_port = None

                if not puppet_master_port:
                    puppet_master_port = get_free_tcp_port(base_port)

                if not puppet_board_port:
                    puppet_board_port = get_free_tcp_port(int(puppet_master_port)+1)

                save_puppet_details_to_file(puppet_fqdn, puppet_master_port, puppet_board_port, projects_authstrings, instance_repo_path+'/.piman.data')

                if debug:
                    print(instance+': puppetmaster assigned port: '+str(puppet_master_port))
                    print(instance+': puppetboard assigned port: '+str(puppet_board_port))

                # TODO: dcogen.py
                docker_compose_override = open(instance_repo_path+'/docker-compose.override.yml', "w+")
                docker_compose_override.write('version: "2.1"\n')
                docker_compose_override.write('services:\n')
                if enable_puppetboard:
                    docker_compose_override.write('  puppetboard:\n')
                    docker_compose_override.write('    ports:\n')
                    docker_compose_override.write('      - '+str(puppet_board_port)+':80/tcp\n')
                    docker_compose_override.write('    environment:\n')
                    docker_compose_override.write("      EYP_PUPPETBOARD_PASSWORD: '"+random_string_lowercase_digits(15)+"'\n")
                docker_compose_override.write('  puppetdb:\n')
                docker_compose_override.write('    environment:\n')
                docker_compose_override.write("      EYP_PUPPETFQDN: '"+puppet_fqdn+"'\n")
                docker_compose_override.write("      EYP_PUPPETDB_EXTERNAL_PORT: '"+str(puppet_master_port)+"'\n")
                docker_compose_override.write("  puppetmaster:\n")
                docker_compose_override.write("    ports:\n")
                docker_compose_override.write("      - "+bind_ip+str(puppet_master_port)+":8140/tcp\n")
                docker_compose_override.write("    environment:\n")
                docker_compose_override.write("      EYP_PUPPETFQDN: '"+puppet_fqdn+"'\n")
                docker_compose_override.write("      EYP_PM_SSL_REPO: '"+instance_ssl_remote+"'\n")
                docker_compose_override.write("      EYP_PM_CUSTOMER_REPO: '"+instance_config_remote+"'\n")
                docker_compose_override.write("      EYP_PM_FILES_REPO: '"+instance_files_remote+"'\n")
                if add_default_network:
                    docker_compose_override.write("    networks:\n")
                    docker_compose_override.write("      default: {}\n")
                docker_compose_override.close()

                git_instance_repo.add('--all')
                git_instance_repo.commit('-vam', 'template')


                buf = StringIO()
                git_instance_repo('ls-remote', '--heads', 'origin', 'master',_out=buf)

                if debug:
                    print("ls-remote: >"+buf.getvalue().strip('\n')+"<")

                if buf.getvalue():
                    git_instance_repo.pull('origin', 'master', '--allow-unrelated-histories', '--no-edit')

                git_instance_repo.push('origin', 'master')

                if debug:
                    print(instance+': INSTANCE repo push origin master')


            #
            # config repo
            #
            config_repo_path = base_dir+'/'+instance+'/.tmp_config_repo'
            os.makedirs(name=config_repo_path, exist_ok=True)

            if debug:
                print("DEBUG: temporal config repo path: "+config_repo_path)

            git_config_repo = sh.git.bake(_cwd=config_repo_path, _env={"EMAIL": author_email, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email, "GIT_SSH_COMMAND": "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"})

            if os.path.isdir(config_repo_path+'/.git'):
                # repo ja colonat
                if debug:
                    print(instance+': config repo ja clonat, refrescant: '+config_repo_path)
                sh.rm("-fr", config_repo_path)
                os.makedirs(name=config_repo_path, exist_ok=True)

            if debug:
                print(instance+': inicialitzant config repo: '+config_repo_path)
            sh.git.clone(instance_config_remote, config_repo_path, _env={"EMAIL": author_email, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": author_email, "GIT_SSH_COMMAND": "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"})

            # Puppetfile
            if not skip_pfgen:
                if not os.path.isfile(config_repo_path+'/Puppetfile'):
                    if debug:
                        print(instance+': generating '+config_repo_path+'/Puppetfile')
                    config_repo_puppetfile = open(config_repo_path+'/Puppetfile', "w+")
                    pfgen.generatePuppetfile(config_file=pfgen_config, write_puppetfile_to=config_repo_puppetfile)
                    config_repo_puppetfile.close()

            # site.pp
            if not os.path.isfile(config_repo_path+'/manifests/site.pp'):
                if debug:
                    print(instance+': generating '+config_repo_path+'/manifests/site.pp')
                os.makedirs(name=config_repo_path+'/manifests', exist_ok=True)
                config_repo_sitepp = open(config_repo_path+'/manifests/site.pp', "w+")
                siteppgen.generatesitepp(config_file=sitepp_config, write_sitepp_to=config_repo_sitepp)
                config_repo_sitepp.close()

            # hiera.yaml
            if not os.path.isfile(config_repo_path+'/hiera.yaml') or refresh_hierayaml:
                if debug:
                    print(instance+': generating '+config_repo_path+'/hiera.yaml')
                config_repo_hierayaml = open(config_repo_path+'/hiera.yaml', "w+")

                if debug:
                    print("projectes: "+str(projects_authstrings))

                hieragen.generatehierayaml(config_file=hierayaml_config, write_hierayaml_to=config_repo_hierayaml, hieradata_base_dir=config_repo_path+'/hieradata', puppet_fqdn=puppet_fqdn, puppet_port=puppet_master_port, create_skel_auth_strings=projects_authstrings)
                config_repo_hierayaml.close()
            else:
                hieragen.generatehieradataskel(config_file=hierayaml_config, hieradata_base_dir=config_repo_path+'/hieradata', create_skel_auth_strings=projects_authstrings)

            git_config_repo.add('--all')
            try:
                git_config_repo.commit('-vam', 'piman '+datetime.datetime.today().strftime('%Y-%m-%d-%H:%M:%S'))
            except:
                pass

            try:
                git_config_repo.branch('production')
            except:
                pass

            git_config_repo.checkout('production')

            try:
                git_config_repo.branch('-d', 'master')
            except:
                pass

            git_config_repo.push('-u', 'origin', 'production')
            git_config_repo.pull('origin', 'production', '--allow-unrelated-histories', '--no-edit')

            if debug:
                print(instance+': CONFIG repo push origin production')

                # deploy instance helpers

                instance_helpers_path = base_dir+'/'+instance
                if not os.path.isfile(instance_repo_path+'/start.sh'):
                    if debug:
                        print(instance+': generating start.sh')

                    start_sh_fh = open(instance_repo_path+'/start.sh', "w+")
                    print('#!/bin/bash', file=start_sh_fh)
                    print('cd '+instance_repo_path, file=start_sh_fh)
                    print('bash update.utils.sh', file=start_sh_fh)
                    print('docker-compose -p '+instance+' up -d', file=start_sh_fh)
                    print('cd $OLDPWD', file=start_sh_fh)
                stat_startsh = os.stat(instance_repo_path+'/start.sh')
                os.chmod(instance_repo_path+'/start.sh', stat_startsh.st_mode | stat.S_IEXEC)
                if not os.path.isfile(instance_helpers_path+'/start.sh') and not os.path.islink(instance_helpers_path+'/start.sh'):
                    os.symlink(instance_repo_path+'/start.sh', instance_helpers_path+'/start.sh')

                if not os.path.isfile(instance_repo_path+'/update.sh'):
                    if debug:
                        print(instance+': generating update.sh')

                    update_sh_fh = open(instance_repo_path+'/update.sh', "w+")
                    print('#!/bin/bash', file=update_sh_fh)
                    print('cd '+instance_repo_path, file=update_sh_fh)
                    print('docker-compose -p '+instance+' exec puppetmaster /usr/local/bin/updatepuppet.sh', file=update_sh_fh)
                    print('cd $OLDPWD', file=update_sh_fh)
                stat_updatesh = os.stat(instance_repo_path+'/update.sh')
                os.chmod(instance_repo_path+'/update.sh', stat_updatesh.st_mode | stat.S_IEXEC)
                if not os.path.isfile(instance_helpers_path+'/update.sh') and not os.path.islink(instance_helpers_path+'/update.sh'):
                    os.symlink(instance_repo_path+'/update.sh', instance_helpers_path+'/update.sh')

                # commit helpers
                git_instance_repo.add('--all')
                try:
                    git_instance_repo.commit('-vam', 'piman helpers - '+datetime.datetime.today().strftime('%Y-%m-%d-%H:%M:%S'))
                except:
                    pass
                git_instance_repo.push('origin', 'master')
