import geoip2.database

class MaxmindDB:

    def __init__(self, conf):
        self.db_path = conf['geo']['maxmind']['db_path']

    def annotate(self, ip):
        reader = geoip2.database.Reader(self.db_path)
        lookup = reader.city(ip)
        reader.close()

        return {
                'city': str(lookup.city.name),
                'latitude': str(lookup.location.latitude),
                'longitude': str(lookup.location.longitude)
                }

    def get_labels(self):
        return ['city', 'latitude', 'longitude']
