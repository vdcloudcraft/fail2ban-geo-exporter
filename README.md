# fail2ban-geo-exporter

It's all in the description already. This little program will expose Prometheus metrics for every IP banned by `fail2ban`. You can have them geotagged or disable tagging if you just want the IP and the jail it's coming from.

NOTE: This software assumes your fail2ban jail definitions are all in a single file. Multiple definites under `jail.d/` are currently not supported.

## Metrics

This exporter provides a single time series named `fail2ban_banned_ip` for each IP in a fail2ban jail.
Default labels are: `jail` and `ip` with their respective values.

More labels can be provided by enabling geoIP annotation. At this point, the maxmind provider adds `city`, `latitude`, and `longitude` in addition the default labels.

A small guide to creating your own geoIP provider can be found in the [Extensibility](#Extensibility) section of this README.

## Installation

Pick your favourite working directory and `git clone https://github.com/vdcloudcraft/fail2ban-geo-exporter.git .`

### As a systemd service

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

Now open `conf.yml` and you should see something like this

```yaml
server:
    port: 
geo:
    enabled: True
    provider: 'MaxmindDB'
    maxmind:
        db_path: '/f2b-exporter/db/GeoLite2-City.mmdb'
f2b:
    conf: '/etc/fail2ban/jail.local'
    db: '/var/lib/fail2ban/fail2ban.sqlite3'
```

Just plug in the port you want your exporter to be listening on. If you want to enable geotagging, there is only one method at this time and for that you will need to sign up for a free account at https://www.maxmind.com, download their city database and plug the path to the db in `geo.maxmind.db_path`. Their paid tier claims to have increased accuracy and is interchangable with their free database, so that should work as a data source for this exporter as well. At the time of writing I can neither deny, nor confirm these claims.

When that is all done, run following commands and your exporter is running and will survive reboots:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fail2ban-geo-exporter.service
sudo service fail2ban-geo-exporter start
```

You should see a list of metrics when you run `curl http://localhost:[port]/metrics`

### As a Docker container

As described in the section before, provide a port and enable/disable geotagging in `conf.yml`

To build the image for Docker run `docker build -t fail2ban-geo-exporter .`
This will include your configuration in the image, so if you don't mount the config itself into the container, the paths inside it are where you need to mount DBs and jail config.

An examplary command to run the container could look like this:
```bash
docker run -d \
        -v /etc/fail2ban/jail.local:/etc/fail2ban/jail.local:ro \
        -v /var/lib/fail2ban/fail2ban.sqlite3:/var/lib/fail2ban/fail2ban.sqlite3:ro \
        -v /<path-to-your-db>/GeoLite2-City.mmdb:/f2b-exporter/db/GeoLite2-City.mmdb \
        --name fail2ban-geo-exporter \
        --restart unless-stopped \
        fail2ban-geo-exporter:latest
```

## Extensibility

Currently there is only one way to geotag IPs and that is with the Maxmind db. But there is a way to provide custom geoIP providers.

If you wish to implement your own method for annotating your IPs, you need to create a Python class and save the module in `./geoip_provider/`

You need to ensure following requirements are fullfilled:
- Your module name is a lower case version of your class name. E.g.: Class `FancyProvider`, module `./geoip_providers/fancyprovider.py`
- Your class implements a method `annotate(ip)`, that takes in a single IP as a string and returns a dictionary with all additional labels for Prometheus to use. Do not include the IP itself as a label.
- Your class implements a method `get_labels()` that returns a list of strings with the label names it's going to provide.

When all that is given, you can just put your class name with[!] capitalization into the configuration under `geo.provider` and enjoy the fruits of your labour.

If you do create another provider class and think other people might find it useful too, I'll gladly review pull requests.

## Grafana dashboard

The file `grafana-dash.json` includes a complete definition to display your banned IPs on a worldmap and count all banned IPs per jail.
