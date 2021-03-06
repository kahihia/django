include:
  - circus
  - database

app-pkgs:
  pkg.installed:
    - names:
      - git
      - python-virtualenv
      - python-dev
      - gcc
      - libjpeg8-dev
      - libpq-dev

ruby:
  pkg.purged

webproject_user:
  user.present:
    - name: webproject
    - gid_from_name: True

gpg-import-D39DC0E3:
    cmd.run:
        - user: webproject
        - require:
            - user: webproject_user
        - name: gpg --keyserver hkp://keys.gnupg.net:80 --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3
        - unless: gpg --fingerprint |fgrep 'Key fingerprint = 409B 6B17 96C2 7546 2A17  0311 3804 BB82 D39D C0E3'

webproject_dirs:
  file.directory:
    - user: webproject
    - group: webproject
    - makedirs: true
    - names:
      - {{ pillar['files']['root_dir'] }}
      - {{ pillar['files']['media_dir'] }}
      - {{ pillar['files']['static_dir'] }}
    - require:
      - user: webproject

webproject_env:
  virtualenv.managed:
    - name: {{ pillar['files']['env_dir'] }}
    - requirements: {{ pillar['files']['clone_dir'] }}requirements-server.txt
    - system_site_packages: false
    - no_deps: true
    - clear: false
    - user: webproject
    - require:
      - pkg: app-pkgs
      - user: webproject
      - file: webproject_dirs

project:
  pip.installed:
    - editable: {{ pillar['files']['clone_dir'] }}
    - bin_env: {{ pillar['files']['env_dir'] }}
    - user: webproject
    - require:
      - virtualenv: webproject_env

django_log_dir:
  file.directory:
    - name: {{ pillar['files']['logs']['django_dir'] }}
    - user: webproject
    - group: webproject
    - mode: 755

webproject_project:
  file.recurse:
    - user: webproject
    - group: webproject
    - name: {{ pillar['files']['project_dir'] }}
    - source: salt://webserver/webproject/
    - template: jinja
    - require:
      - file: django_log_dir
      - virtualenv: {{ pillar['files']['env_dir'] }}
      - service: postgresql

postfix:
  pkg:
    - latest
  service:
    - running

nginx:
  user:
    - present
  pkg:
    - latest
  service:
    - running
    - watch:
      - file: nginx_conf
      - file: ssl_crt
      - file: ssl_key
      - file: dhparam
      - file: gandi_plus_intermediates_crt
    - require:
        - pkg: nginx

nginx_conf:
  file.managed:
    - name: /etc/nginx/sites-available/default
    - source: salt://webserver/nginx.conf
    - template: jinja
    - makedirs: True
    - mode: 755
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx

crt_dir:
  file.directory:
    - name: {{ pillar['files']['crt_dir'] }}
    - makedirs: True
    - mode: 755
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx

ssl_crt:
  file.managed:
    - name: {{ pillar['files']['crt_dir'] }}dancerfly.crt
    - contents: |-
        {{ pillar['deploy']['dancerfly_ssl_crt']|indent(8) }}
        {{ pillar['deploy']['gandi_plus_intermediates_ssl_crt']|indent(8) }}
    - mode: 400
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx
      - file: crt_dir

gandi_plus_intermediates_crt:
  file.managed:
    - name: {{ pillar['files']['crt_dir'] }}gandi_plus_intermediates.crt
    - contents: |-
        {{ pillar['deploy']['gandi_plus_intermediates_ssl_crt']|indent(8) }}
    - mode: 400
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx
      - file: crt_dir

ssl_key:
  file.managed:
    - name: {{ pillar['files']['crt_dir'] }}dancerfly.key
    - contents: |-
        {{ pillar['deploy']['ssl_key']|indent(8) }}
    - mode: 400
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx
      - file: crt_dir

dhparam:
  file.managed:
    - name: {{ pillar['files']['crt_dir'] }}dhparam.pem
    - contents: |-
        {{ pillar['deploy']['dhparam']|indent(8) }}
    - mode: 400
    - user: nginx
    - group: nginx
    - require:
      - pkg: nginx
      - file: crt_dir

eventlet:
  pip.installed:
    - bin_env: {{ pillar['files']['env_dir'] }}
    - user: webproject
    - require:
      - virtualenv: webproject_env

gunicorn:
  pip.installed:
    - name: gunicorn==19.1.1
    - bin_env: {{ pillar['files']['env_dir'] }}
    - user: webproject
    - require:
      - virtualenv: webproject_env
      - pip: eventlet

gunicorn_log:
  file.managed:
    - name: {{ pillar['files']['logs']['gunicorn'] }}
    - user: webproject
    - group: webproject
    - mode: 644
    - require:
      - pip: gunicorn

gunicorn_circus:
  file.managed:
    - name: /etc/circus.d/gunicorn.ini
    - source: salt://webserver/gunicorn.ini
    - makedirs: True
    - template: jinja
    - require:
      - file: gunicorn_log
      - user: webproject_user
      - virtualenv: webproject_env
    - watch_in:
      - service: circusd
  cmd.wait:
    - name: circusctl restart gunicorn
    - watch:
      - file: webproject_project
      - file: gunicorn_circus
      - virtualenv: webproject_env
    - require:
      - service: circusd

gunicorn_circus_start:
  cmd.run:
    - name: circusctl start gunicorn
    - require:
      - file: webproject_project
      - file: gunicorn_circus
      - virtualenv: webproject_env
    - onlyif: "[ `circusctl status gunicorn` == 'stopped' ]"

dwolla_update_tokens:
  cron.present:
    - user: webproject
    - name: {{ pillar['files']['env_dir'] }}bin/python {{ pillar['files']['project_dir'] }}manage.py update_tokens --days=15
    - hour: 6
    - minute: 0


send_daily_emails:
  cron.present:
    - user: webproject
    - name: {{ pillar['files']['env_dir'] }}bin/python {{ pillar['files']['project_dir'] }}manage.py send_daily_emails
    - hour: 18
    - minute: 0
