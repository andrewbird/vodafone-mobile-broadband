%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           bcm
Version:        %(%{__python} -c 'from wader.bcm.consts import APP_VERSION; print APP_VERSION')
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

BuildRequires:  wader-core >= 0.5.7, python-imaging, gettext
Requires:       python >= 2.5, wader-core >= 0.5.7, python-messaging >= 0.5.10

%description
Betavine Connection Manager is a tool that manages 3G devices and mobile phones,
faciliating Internet connection, sending/receiving SMS, managing contacts, usage
statistics, prepay top up and suchlike.

%prep
%setup -q -n %{name}-%{version}
# remove dangling link
rm -f wader/common
# replace it with the installed version
ln -s %{python_sitelib}/wader/common wader/.

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot} --prefix=%{_prefix}

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%post
:

%files
%defattr(-,root,root)
%{python_sitelib}/Betavine_Connection_Manager-*
%dir %{python_sitelib}/wader/bcm/
%dir %{python_sitelib}/wader/bcm/contacts/
%dir %{python_sitelib}/wader/bcm/contrib/
%dir %{python_sitelib}/wader/bcm/contrib/pycocuma/
%dir %{python_sitelib}/wader/bcm/contrib/gtkmvc/
%dir %{python_sitelib}/wader/bcm/contrib/gtkmvc/adapters/
%dir %{python_sitelib}/wader/bcm/contrib/gtkmvc/progen/
%dir %{python_sitelib}/wader/bcm/contrib/gtkmvc/support/
%dir %{python_sitelib}/wader/bcm/controllers/
%dir %{python_sitelib}/wader/bcm/models/
%dir %{python_sitelib}/wader/bcm/views/
%dir /usr/share/bcm/resources/glade/

%{python_sitelib}/wader/bcm/*.py
%{python_sitelib}/wader/bcm/*.py[co]
%{python_sitelib}/wader/bcm/contacts/*.py
%{python_sitelib}/wader/bcm/contacts/*.py[co]
%{python_sitelib}/wader/bcm/contrib/*.py
%{python_sitelib}/wader/bcm/contrib/*.py[co]
%{python_sitelib}/wader/bcm/contrib/gtkmvc/*.py
%{python_sitelib}/wader/bcm/contrib/gtkmvc/*.py[co]
%{python_sitelib}/wader/bcm/contrib/gtkmvc/*/*.py
%{python_sitelib}/wader/bcm/contrib/gtkmvc/*/*.py[co]
%{python_sitelib}/wader/bcm/contrib/pycocuma/*.py
%{python_sitelib}/wader/bcm/contrib/pycocuma/*.py[co]
%{python_sitelib}/wader/bcm/controllers/*.py
%{python_sitelib}/wader/bcm/controllers/*.py[co]
%{python_sitelib}/wader/bcm/models/*.py
%{python_sitelib}/wader/bcm/models/*.py[co]
%{python_sitelib}/wader/bcm/views/*.py
%{python_sitelib}/wader/bcm/views/*.py[co]
/usr/share/bcm/resources/glade/*

%{_bindir}/bcm
/usr/share/locale/*/LC_MESSAGES/bcm.mo
/usr/share/applications/bcm.desktop
/usr/share/pixmaps/bcm.png
/etc/dbus-1/system.d/bcm.conf

%doc README

%changelog
* Sun Sep 11 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.14
- 0.5.6 New Release
* Tue Jun 07 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.13
- 0.5.6 Create Spec file
