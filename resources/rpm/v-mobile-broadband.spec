%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           v-mobile-broadband
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

BuildRequires:  python-imaging, gnu-free-sans-fonts, gettext
Requires:       python >= 2.5, wader-core >= 0.5.11, python-messaging >= 0.5.10, python-dateutil

%description
V Mobile Broadband is a tool that manages 3G devices and mobile phones,
faciliating Internet connection, sending/receiving SMS, managing contacts, usage
statistics, prepay top up and suchlike.

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} -c 'import setuptools; execfile("setup.py")' build

%install
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --root %{buildroot} --prefix=%{_prefix} --install-lib=/usr/share/%{name}
(mkdir %{buildroot}/usr/bin && \
	cd %{buildroot}/usr/bin && \
	ln -s ../share/%{name}/bin/%{name} .)

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%post
:

%files
%defattr(-,root,root)
/usr/share/%{name}/V_Mobile_Broadband-*
%dir /usr/share/%{name}/gui/
%dir /usr/share/%{name}/gui/contacts/
%dir /usr/share/%{name}/gui/contrib/
%dir /usr/share/%{name}/gui/contrib/pycocuma/
%dir /usr/share/%{name}/gui/contrib/gtkmvc/
%dir /usr/share/%{name}/gui/contrib/gtkmvc/adapters/
%dir /usr/share/%{name}/gui/contrib/gtkmvc/progen/
%dir /usr/share/%{name}/gui/contrib/gtkmvc/support/
%dir /usr/share/%{name}/gui/controllers/
%dir /usr/share/%{name}/gui/models/
%dir /usr/share/%{name}/gui/views/
%dir /usr/share/%{name}/resources/glade/

/usr/share/%{name}/gui/*.py
/usr/share/%{name}/gui/*.py[co]
/usr/share/%{name}/gui/contacts/*.py
/usr/share/%{name}/gui/contacts/*.py[co]
/usr/share/%{name}/gui/contrib/*.py
/usr/share/%{name}/gui/contrib/*.py[co]
/usr/share/%{name}/gui/contrib/gtkmvc/*.py
/usr/share/%{name}/gui/contrib/gtkmvc/*.py[co]
/usr/share/%{name}/gui/contrib/gtkmvc/*/*.py
/usr/share/%{name}/gui/contrib/gtkmvc/*/*.py[co]
/usr/share/%{name}/gui/contrib/pycocuma/*.py
/usr/share/%{name}/gui/contrib/pycocuma/*.py[co]
/usr/share/%{name}/gui/controllers/*.py
/usr/share/%{name}/gui/controllers/*.py[co]
/usr/share/%{name}/gui/models/*.py
/usr/share/%{name}/gui/models/*.py[co]
/usr/share/%{name}/gui/views/*.py
/usr/share/%{name}/gui/views/*.py[co]
/usr/share/%{name}/resources/glade/*

%{_bindir}/%{name}
/usr/share/%{name}/bin/%{name}
/usr/share/locale/*/LC_MESSAGES/%{name}.mo
/usr/share/applications/%{name}.desktop
/usr/share/pixmaps/%{name}.png
/etc/dbus-1/system.d/%{name}.conf

%doc README

%changelog
* Fri May 18 2012 Andrew Bird <ajb@spheresystems.co.uk> 3.00.00
- 0.5.6 Package got renamed
* Tue Nov 15 2011 Andrew Bird <ajb@spheresystems.co.uk> 3.00.00
- 0.5.6 New Release
* Tue Nov 15 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.15
- 0.5.6 Package got renamed
* Sun Sep 11 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.14
- 0.5.6 New Release
* Tue Jun 07 2011 Andrew Bird <ajb@spheresystems.co.uk> 2.99.13
- 0.5.6 Create Spec file
