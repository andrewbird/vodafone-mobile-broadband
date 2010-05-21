all:
	dpkg-buildpackage -rfakeroot

clean:
	rm -rf build debian/bcm debian/bcm.* Bcm.egg-info

