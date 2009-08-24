
from wader.vmc.contacts.contact_evolution import EVContact, EVContactsManager
from wader.vmc.contacts.contact_kdepim import KDEContact, KDEContactsManager

supported_types = [ (EVContact, EVContactsManager),
                    (KDEContact, KDEContactsManager),
                  ]
