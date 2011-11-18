DOMAIN = vodafone-mobile-broadband

all:

create:
	xgettext -d$(DOMAIN) -LGlade ../glade/*.glade -o $(DOMAIN).pot
	xgettext --from-code=utf-8 -k_ -d$(DOMAIN) -LPython `find ../../gui -name "*.py"` ../../bin/vodafone-mobile-broadband -o $(DOMAIN).pot -j

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
