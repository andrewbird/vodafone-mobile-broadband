
from wader.vmc.contacts.contact_evolution import EVContact, EVContactsManager
from wader.vmc.contacts.contact_kdepim import KDEContact, KDEContactsManager
from wader.vmc.contacts.contact_axiom import ADBContact, ADBContactsManager

supported_types = [ (EVContact, EVContactsManager),
                    (KDEContact, KDEContactsManager),
                    (ADBContact, ADBContactsManager),
                  ]
