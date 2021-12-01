# python-piman

## piman - Puppet Instance MANager

### config file

piman.config

```
[piman]
base-dir = /home/jordi/piman
instance-template = https://github.com/jordiprats/docker-puppetmaster5
puppet-fqdn = puppetmaster5.systemadmin.es
base-port = 8140
debug = true

pfgen-config = ./pfgen.config

[tachi]

projects = [ "tachi" ]

config = git@gitlab.com:demopuppet/demo-config.git
ssl = git@gitlab.com:demopuppet/demo-ssl.git
files = git@gitlab.com:demopuppet/demo-files.git
instance = git@gitlab.com:demopuppet/demo-instance.git
```

## pfgen - Puppetfile generator

### config file

pfgen.config

```
[github]
token =  GITHUB_PAT_HERE
debug=false

[jordiprats]
skip-forked-repos=true
repo-pattern="eyp-"
current-version=True

[nttcom-ms]
skip-forked-repos=true
repo-pattern="eyp-"
current-version=True

[saltait]
skip-forked-repos=true
repo-pattern="eyp-"
current-version=True

[puppetlabs/puppetlabs-stdlib]
version=6.1.0

[eyp/eyp-demo]
url = 'ssh://git@gitlab.demo.systemadmin.es:7999/eyp/eyp-demo.git'
```

## hieragen

### config file

hieragen.config

```
[hieragen]

debug = true
auth-facts = [ "eypconf_platformid", "eypconf_magic_hash" ]
```

## siteppgen

### config file

siteppgen.config

```
[sitegen]
debug = true
deep-include-classes = [ "classes" ]
resource-file = ./siteppgen/resource.list
resource-hash = { "cronjobs": "cron", "crontabs": "cron" }

[common_packages]
resource-name = package
merge-strategy = deep

[paquets]
resource-name = package
merge-strategy = deep

[base_packages]
resource-name = package
merge-strategy = deep

[plain_mounts]
resource-name = mount
merge-strategy = deep

[plain_execs]
resource-name = exec
merge-strategy = deep

[etchosts]
resource-name = host
merge-strategy = deep

[sshkeys]
resource-name = ssh_authorized_key
merge-strategy = deep

[knownhosts]
resource-name = sshkey
merge-strategy = deep

[sshprivkeys]
resource-name = openssh::privkey
merge-strategy = deep

[sshmatch]
resource-name = openssh::match
merge-strategy = deep

[sudos]
resource-name = sudoers::sudo
merge-strategy = deep

[security_limits]
resource-name = pam::limit
merge-strategy = deep

[modprobeinstall]
resource-name = modprobe::install
merge-strategy = deep

[haproxystats]
resource-name = haproxy::stats

[haproxybackendhttprequestdenies]
resource-name = haproxy::backend::http_request_deny

[nginxproxypasses]
resource-name = nginx::proxypass
```
