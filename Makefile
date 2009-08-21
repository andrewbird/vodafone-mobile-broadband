all:
	dpkg-buildpackage -rfakeroot

clean:
	rm -rf build debian/wader-vmc debian/wader-vmc.* Wader_VMC.egg-info
	make -C resources/po clean

