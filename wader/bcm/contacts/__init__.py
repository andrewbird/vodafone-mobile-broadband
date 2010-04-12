
from wader.bcm.contacts.contact_evolution import EVContact, EVContactsManager
from wader.bcm.contacts.contact_kdepim import KDEContact, KDEContactsManager
from wader.bcm.contacts.contact_sim import SIMContact, SIMContactsManager

supported_types = [
    (EVContact, EVContactsManager),
    (KDEContact, KDEContactsManager),
    (SIMContact, SIMContactsManager),
]
