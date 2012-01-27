DOMAIN = vodafone-mobile-broadband

all:

create:
	xgettext -d$(DOMAIN) -LGlade ../glade/*.glade -o $(DOMAIN).pot
	xgettext --from-code=utf-8 -k_ -d$(DOMAIN) -LPython `find ../../gui -name "*.py"` ../../bin/vodafone-mobile-broadband -o $(DOMAIN).pot -j
	# Tidy output to be more like launchpad's
	sed -i $(DOMAIN).pot \
		-e '1,5d' \
		-e '/^\"Language:/d' \
		-e 's/CHARSET/UTF-8/g'

merge:
	for po in *.po; do \
		lingua=`basename $$po .po`; \
	        mv $$lingua.po $$lingua.old.po; \
		if msgmerge -o $$lingua.po $$lingua.old.po $(DOMAIN).pot; then \
		    rm $$lingua.old.po; \
		else \
		    rm -f $$lingua.po; \
		    mv $$lingua.old.po $$lingua.po; \
		fi \
	done

.PHONY: create merge
