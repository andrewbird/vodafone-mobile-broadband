from networks import NetworkOperator

class MovistarSpain(NetworkOperator):
    netid = ["21402", "21407"]
    name = "Movistar"
    country = "Spain"
    type = ""
    smsc = "+34609090909"
    apn = "movistar.es"
    username = "movistar"
    password = "movistar"
    dns1 = "194.179.001.100"
    dns2 = "194.179.001.101"


class YoigoSpain(NetworkOperator):
    netid = ["21404", "21401"]
    name = "Yoigo"
    country = "Spain"
    type = ""
    smsc = "+34600000000"
    apn = "internet"
    username = "yoigo"
    password = "yoigo"
    dns1 = "10.8.0.20"
    dns2 = "10.8.0.21"


class NetComNorway(NetworkOperator):
    netid = ["24202"]
    name = "NetCom"
    country = "Norway"
    type = ""
    smsc = "+4792001000"
    apn = "internet"
    username = "internet"
    password = "internet"
    dns1 = "212.169.123.67"
    dns2 = "212.45.188.254"


class TelkomSelIndonesia(NetworkOperator):
    netid = ["51010"]
    name = "TelkomSel"
    country = "Indonesia"
    type = ""
    smsc = "+6281100000"
    apn = "flash"
    username = "flash"
    password = "flash"
    dns1 = "202.3.208.10"
    dns2 = "202.3.210.10"


class SATelindoIndonesia(NetworkOperator):
    netid = ["51001"]
    name = "PT. SATelindo C"
    country = "Indonesia"
    type = ""
    smsc = "+62816124"
    apn = "indosat3g"
    username = "indosat"
    password = "indosat"
    dns1 = "202.155.46.66"
    dns2 = "202.155.46.77"


class IM3Indonesia(NetworkOperator):
    netid = ["51021"]
    name = "IM3"
    country = "Indonesia"
    type = ""
    smsc = "+62855000000"
    apn = "www.indosat-m3.net"
    username = "im3"
    password = "im3"
    dns1 = "202.155.46.66"
    dns2 = "202.155.46.77"


class ProXLndonesia(NetworkOperator):
    netid = ["51011"]
    name = "Pro XL"
    country = "Indonesia"
    type = ""
    smsc = "+62818445009"
    apn = "www.xlgprs.net"
    username = "xlgprs"
    password = "proxl"
    dns1 = "202.152.254.245"
    dns2 = "202.152.254.246"


class TMNPortugal(NetworkOperator):
    netid = ["26806"]
    name = "TMN"
    country = "Portugal"
    type = ""
    smsc = "+351936210000"
    apn = "internet"
    username = "tmn"
    password = "tmnnet"
    dns1 = None
    dns2 = None


class ThreeItaly(NetworkOperator):
    netid = ["22299"]
    name = "3"
    country = "Italy"
    type = ""
    smsc = "+393916263333"
    apn = "naviga.tre.it"
    username = "anon"
    password = "anon"
    dns1 = "62.13.171.1"
    dns2 = "62.13.171.2"


class ThreeAustralia(NetworkOperator):
    netid = ["50506"]
    name = "3"
    country = "Australia"
    type = ""
    smsc = "+61430004010"
    apn = "3netaccess"
    username = "*"
    password = "*"
    dns1 = None
    dns2 = None


class TimItaly(NetworkOperator):
    netid = ["22201"]
    name = "TIM"
    country = "Italy"
    type = ""
    smsc = "+393359609600"
    apn = "ibox.tim.it"
    username = "anon"
    password = "anon"
    dns1 = None
    dns2 = None


class WindItaly(NetworkOperator):
    netid = ["22288"]
    name = "Wind"
    country = "Italy"
    type = ""
    smsc = "+393205858500"
    apn = "internet.wind"
    username = "anon"
    password = "anon"
    dns1 = None
    dns2 = None

