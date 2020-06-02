# fail2ban-geo-exporter

It's all in the description already. This little program will expose Prometheus metrics for every IP banned by `fail2ban`. You can have them geotagged or disable tagging if you just want the IP and the jail it's coming from.

NOTE: This software assumes your fail2ban jail definitions are all in a single file. Multiple definites under `jail.d/` are currently not supported.

## Disclaimer

This exporter goes deliberately against best practices and ist not suitable for deployments at scale. It's intended to be used in a homelab alike setting and won't even provide any sane metric to alert on. This may change in the future, but it more than likely will not.

By enabling grouping in the `conf.yml`, the growth of label cardinality can be reduced, but this is still far from ideal.

## Metrics

This exporter provides a single time series named `fail2ban_banned_ip` for each IP in a fail2ban jail.
Default labels are: `jail` and `ip` with their respective values.

More labels can be provided by enabling geoIP annotation. At this point, the maxmind provider adds `city`, `latitude`, and `longitude` in addition the default labels.

If you enable grouping in the `conf.yml`, you will instead receive two sets of metrics and no more data about single IPs. Instead you get a gauge `fail2ban_location` which counts the number of banned IPs per location. The labels are the same as above, just without `jail` and `ip`.

The second metric is `fail2ban_jailed_ips` which is a gauge, that displays all currently banned IPs per jail. `jail` is the only label in this metric.

It's highly recommended to enable grouping, in order to reduce the cardinality of your labels.

A small guide to creating your own geoIP provider can be found in the [Extensibility](#Extensibility) section of this README.


## Configuration

```yaml
server:
    listen_address:
    port:
geo:
    enabled: True
    provider: 'MaxmindDB'
    enable_grouping: False
    maxmind:
        db_path: '/f2b-exporter/db/GeoLite2-City.mmdb'
f2b:
    conf_path: '/etc/fail2ban'
    db: '/var/lib/fail2ban/fail2ban.sqlite3'
```

Just plug in the port and IPv4 address you want your exporter to be listening on. If you want to enable geotagging, there is only one method at this time and for that you will need to sign up for a free account at https://www.maxmind.com, download their city database and plug the path to the db in `geo.maxmind.db_path`. Their paid tier claims to have increased accuracy and is interchangable with their free database, so that should work as a data source for this exporter as well. At the time of writing I can neither deny, nor confirm these claims.

`f2b.conf_path` assumes default directory structure of fail2ban. So your jails can be defined in `/etc/fail2ban/jail.local` or in `/etc/fail2ban/jail.d/*.local`. Default values defined in `jail.local` (i.e.: bantime) will be picked up and consequently applied to all jails defined under `jail.d`.

Missing entries in the MaxmindDB will be discarded by default. If you want to keep track of missing entries, you can provide default values to be used instead. In your `conf.yml` add a section under `geo.maxmind` like so:

```yaml
geo:
    maxmind:
        on_error:
            city: 'Atlantis'
            latitude: '0'
            longitude: '0'
```
## Installation

### As a systemd service

Pick your favourite working directory and `git clone https://github.com/vdcloudcraft/fail2ban-geo-exporter.git .`

Now run these commands to set up a python virtual environment:

```bash
python -m venv .
. bin/activate
pip install -r requirements.txt
```

Create a file called `fail2ban-geo-exporter.service` at `/etc/systemd/system/`

Open that file and paste following content in there:

```bash
[Unit]
Description=fail2ban geo exporter
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=<path>
Environment=PYTHONPATH=<path>/bin
ExecStart=<path>/bin/python3 <path>/fail2ban-exporter.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Make sure to replace all four(4) instances of `<path>` in that config with your actual working directory.

Make sure you have a `conf.yml` in your working directory as described in [Configuration](#configuration)

When that is all done, run following commands and your exporter is running and will survive reboots:

```bash
sudo systemctl daemon-reload
sudo systemctl enable fail2ban-geo-exporter.service
sudo service fail2ban-geo-exporter start
```

You should see a list of metrics when you run `curl http://localhost:[port]/metrics`

### As a Docker container

Make sure you have prepared a config as described in [Configuration](#configuration).

Docker images are provided via [Docker Hub](https://hub.docker.com/repository/docker/vdcloudcraft/fail2ban-geo-exporter)

To run the exporter in a Docker container, execute the following command

```bash
docker run -d \
        -v /etc/fail2ban:/etc/fail2ban:ro \
        -v /var/lib/fail2ban/fail2ban.sqlite3:/var/lib/fail2ban/fail2ban.sqlite3:ro \
        -v /<path-to-your-db>/GeoLite2-City.mmdb:/f2b-exporter/db/GeoLite2-City.mmdb:ro \
        -v /<path-to-your-conf.yml>/conf.yml:/f2b-exporter/conf.yml \
        --name fail2ban-geo-exporter \
        --restart unless-stopped \
        vdcloudcraft/fail2ban-geo-exporter:latest
```

Make sure that your paths to `jail.local` and `fail2ban.sqlite3` are correct.

## Extensibility

Currently there is only one way to geotag IPs and that is with the Maxmind db. But there is a way to provide custom geoIP providers.

If you wish to implement your own method for annotating your IPs, you need to create a Python class and save the module in `./geoip_provider/`

You need to ensure following requirements are fullfilled:

- Your module name is a lower case version of your class name. E.g.: Class `FancyProvider`, module `./geoip_providers/fancyprovider.py`
- Your class has a constructor that accepts a single parameter. This will be the parsed `conf.yml` that will be passed to the class.
- Your class implements a method `annotate(ip)`, that takes in a single IP as a string and returns a dictionary with all additional labels for Prometheus to use. Do not include the IP itself as a label.
- Your class implements a method `get_labels()` that returns a list of strings with the label names it's going to provide.

When all that is given, you can just put your class name with[!] capitalization into the configuration under `geo.provider` and enjoy the fruits of your labour.

Be aware that the `enable_grouping` setting will use only the labels provided by your class to aggregate locations.

If you do create another provider class and think other people might find it useful too, I'll gladly review pull requests.

## Grafana dashboard

The files `dashboard-*.json` include a complete definition for either grouping configuration to display your banned IPs on a worldmap and count all banned IPs per jail.
