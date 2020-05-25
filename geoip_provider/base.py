class BaseProvider:
    def __init__(self, conf):
        pass

    def annotate(self, ip):
        return {}

    def get_labels(self):
        return []
