DATADIR = $(ROOT)/usr/share
LOCALEDIR = $(DATADIR)/locale
DOMAIN = VMC

all: mo

#create pot file
create:
	:
	#xgettext -d$(DOMAIN) -LGlade ../glade/*.glade -o $(DOMAIN).pot
	#xgettext --from-code=utf-8 -k_ -d$(DOMAIN) -LPython `find ../../wader -name "*.py"` ../../bin/wader-vmc -o $(DOMAIN).pot -j

#update all po fles
update-po: $(DOMAIN).pot create
	:
	#for po in *.po; do \
	#	lingua=`basename $$po .po`; \
	#        mv $$lingua.po $$lingua.old.po; \
	#	if msgmerge -o $$lingua.po $$lingua.old.po $(DOMAIN).pot; then \
	#	    rm $$lingua.old.po; \
	#	    if [ -z "$(VERSION)" ] ; then \
	#		VERSION="Unknown"; \
	#	    fi; \
	#	    sed -i -e "s/Project-Id-Version:.*/Project-Id-Version: $(VERSION)\\\n\"/" $$lingua.po; \
	#	else \
	#	    rm -f $$lingua.po; \
	#	    mv $$lingua.old.po $$lingua.po; \
	#	fi \
	#done

#create all mo files
mo: update-po
	:
	mkdir -p locale
	#for po in *.po; do \
	#	lingua=`basename $$po .po` ; \
	#	msgfmt -cf -o $$lingua.mo $$po ; \
	#	mkdir -p locale/$$lingua/LC_MESSAGES/ ; \
	#	ln -f $$lingua.mo locale/$$lingua/LC_MESSAGES/$(DOMAIN).mo ; \
	#done

install: mo
	:
	#for mo in *.mo; do \
	#	lingua=`basename $$mo .mo`; \
	#	install -D --mode=644 $$lingua.mo $(LOCALEDIR)/$$lingua/LC_MESSAGES/$(DOMAIN).mo ; \
	#done

clean:
	rm -Rf locale
	rm -f *.mo

.PHONY: create update-po mo install clean
