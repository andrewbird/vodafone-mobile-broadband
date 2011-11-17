
from wader.vmb.contacts.contact_evolution import EVContact, EVContactsManager
from wader.vmb.contacts.contact_kdepim import KDEContact, KDEContactsManager
from wader.vmb.contacts.contact_sim import SIMContact, SIMContactsManager

supported_types = [
    (EVContact, EVContactsManager),
    (KDEContact, KDEContactsManager),
    (SIMContact, SIMContactsManager),
]
