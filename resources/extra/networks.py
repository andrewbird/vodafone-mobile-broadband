class NetworkOperator(object):
    netid = []
    name = None
    country = None
    type = None
    smsc = None
    apn = None
    username = None
    password = None
    dns1 = None
    dns2 = None

    def __repr__(self):
        args = (self.name, self.country, self.netid[0])
        return "<NetworkOperator %s%s netid: %s>" % args
