%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           vodafone-mobile-broadband
Version:        %(%{__python} -c 'from gui.consts import APP_VERSION; print APP_VERSION')
Release:        1%{?dist}
Summary:        A Mobile Connection Manager written in Python
Source:         ftp://ftp.noexists.org/pub/wader/%{name}-%{version}.tar.bz2
Group:          Applications/Telephony
License:        GPL
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

BuildRequires:  python-devel
%if 0%{?fedora} >= 8
BuildRequires:  python-setuptools-devel
%else
BuildRequires:  python-setuptools
%endif

%if 0%{?suse_version}
BuildRequires:  dbus-1-python, python-tz
Requires:       dbus-1-python, python-tz, python-zopeinterface
Requires:       python-gnome2, python-gnomekeyring, python-gtk2, python-gconf, python-glade2, python-wnck
%else
BuildRequires:  dbus-python, pytz
Requires:       dbus-python, pytz, python-zope-interface
Requires:       gnome-python2-gnome, gnome-python2-gnomekeyring, gnome-python2-gconf, pygtk2, pygtk2-libglade, gnome-python2-libwnck
%endif

BuildRequires:  python-imaging, gettext
Requires:       python >= 2.5, wader-core >= 0.5.7, python-messaging >= 0.5.10

%description
Vodafone Mobile Broadband is a tool that manages 3G devices and mobile phones,
faciliating Internet connection, sending/receiving SMS, managing contacts, usage
statistics, prepay top up and suchlike.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot} --prefix=%{_prefix} --install-lib=/usr/share/vodafone-mobile-broadband
(mkdir %{buildroot}/usr/bin && \
	cd %{buildroot}/usr/bin && \
	ln -s ../share/vodafone-mobile-broadband/vodafone-mobile-broadband .)

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%post
:

%files
%defattr(-,root,root)
/usr/share/vodafone-mobile-broadband/Vodafone_Mobile_Broadband-*
%dir /usr/share/vodafone-mobile-broadband/gui/
%dir /usr/share/vodafone-mobile-broadband/gui/contacts/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/pycocuma/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/adapters/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/progen/
%dir /usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/support/
%dir /usr/share/vodafone-mobile-broadband/gui/controllers/
%dir /usr/share/vodafone-mobile-broadband/gui/models/
%dir /usr/share/vodafone-mobile-broadband/gui/views/
%dir /usr/share/vodafone-mobile-broadband/resources/glade/

/usr/share/vodafone-mobile-broadband/gui/*.py
/usr/share/vodafone-mobile-broadband/gui/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/contacts/*.py
/usr/share/vodafone-mobile-broadband/gui/contacts/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/contrib/*.py
/usr/share/vodafone-mobile-broadband/gui/contrib/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/*.py
/usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/*/*.py
/usr/share/vodafone-mobile-broadband/gui/contrib/gtkmvc/*/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/contrib/pycocuma/*.py
/usr/share/vodafone-mobile-broadband/gui/contrib/pycocuma/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/controllers/*.py
/usr/share/vodafone-mobile-broadband/gui/controllers/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/models/*.py
/usr/share/vodafone-mobile-broadband/gui/models/*.py[co]
/usr/share/vodafone-mobile-broadband/gui/views/*.py
/usr/share/vodafone-mobile-broadband/gui/views/*.py[co]
/usr/share/vodafone-mobile-broadband/resources/glade/*

%{_bindir}/vodafone-mobile-broadband
/usr/share/vodafone-mobile-broadband/vodafone-mobile-broadband
/usr/share/locale/*/LC_MESSAGES/vodafone-mobile-broadband.mo
/usr/share/applications/vodafone-mobile-broadband.desktop
/usr/share/pixmaps/vodafone-mobile-broadband.png
/etc/dbus-1/system.d/vodafone-mobile-broadband.conf

%doc README

%changelog
* Tue Nov 15 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.15
- 0.5.6 Package got renamed
* Sun Sep 11 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.14
- 0.5.6 New Release
* Tue Jun 07 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.13
- 0.5.6 Create Spec file
