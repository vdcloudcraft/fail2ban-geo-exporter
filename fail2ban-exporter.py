import importlib
import yaml
import configparser
import sqlite3
from prometheus_client import make_wsgi_app
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from wsgiref.simple_server import make_server

class Jail:
    def __init__(self, name):
        self.name = name
        self.ip_list = []
        self.bantime = 0

class F2bCollector(object):
    def __init__(self, conf):
        self.geo_provider = self._import_provider(conf)
        self.f2b_conf = conf['f2b']['conf']
        self.f2b_db = conf['f2b']['db']
        self.jails = []
        self.extra_labels = sorted(self.geo_provider.get_labels())

    def _import_provider(self, conf):
        if conf['geo']['enabled']:
            class_name = conf['geo']['provider']
            mod = __import__('geoip_provider.{}'.format(class_name.lower()), fromlist=[class_name])
        else:
            class_name = 'BaseProvider'
            mod = __import__('geoip_provider.base', fromlist=['BaseProvider'])

        GeoProvider = getattr(mod, class_name)
        return GeoProvider(conf)

    def get_jailed_ips(self):
        self.jails.clear()

        conn = sqlite3.connect(self.f2b_db)
        cur = conn.cursor()

        config = configparser.ConfigParser()
        config.read(self.f2b_conf)

        active_jails = cur.execute('SELECT name FROM jails WHERE enabled = 1').fetchall()

        for j in active_jails:
            jail = Jail(j[0])
            bantime = config[j[0]]['bantime'].split(';')[0].strip()
            jail.bantime = int(bantime)
            self.jails.append(jail)

        for jail in self.jails:
            rows = cur.execute('SELECT ip FROM bans WHERE DATETIME(timeofban + ?, \'unixepoch\') > DATETIME(\'now\') AND jail = ?', [jail.bantime, jail.name]).fetchall()
            for row in rows:
                jail.ip_list.append({'ip':row[0]})

        conn.close()

    def assign_location(self):
        for jail in self.jails:
            for entry in jail.ip_list:
                entry.update(self.geo_provider.annotate(entry['ip']))

    def collect(self):
        self.get_jailed_ips()
        self.assign_location()

        metric_labels = ['jail','ip'] + self.extra_labels
        ip_gauge = GaugeMetricFamily('fail2ban_banned_ip', 'IP banned by fail2ban', labels=metric_labels)

        for jail in self.jails:
            for entry in jail.ip_list:
                values = [jail.name, entry['ip']] + [entry[x] for x in self.extra_labels]
                ip_gauge.add_metric(values, 1)

        yield ip_gauge

if __name__ == '__main__':
    with open('conf.yml') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)

    REGISTRY.register(F2bCollector(conf))

    app = make_wsgi_app()
    httpd = make_server('', conf['server']['port'], app)
    httpd.serve_forever()
