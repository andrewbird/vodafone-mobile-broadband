
from gui.contacts.contact_evolution import EVContact, EVContactsManager
from gui.contacts.contact_kdepim import KDEContact, KDEContactsManager
from gui.contacts.contact_sim import SIMContact, SIMContactsManager

supported_types = [
    (EVContact, EVContactsManager),
    (KDEContact, KDEContactsManager),
    (SIMContact, SIMContactsManager),
]
