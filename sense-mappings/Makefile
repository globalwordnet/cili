all:
	for file in http://wordnetcode.princeton.edu/1.5/wn15.zip \
		http://wordnetcode.princeton.edu/1.6/wn16.unix.tar.gz \
		http://wordnetcode.princeton.edu/1.7/wn17.unix.tar.gz \
		http://wordnetcode.princeton.edu/1.7.1/WordNet-1.7.1.tar.gz \
		http://wordnetcode.princeton.edu/2.0/WordNet-2.0.tar.gz \
		http://wordnetcode.princeton.edu/2.1/WordNet-2.1.tar.gz \
		http://wordnetcode.princeton.edu/3.0/WordNet-3.0.tar.gz \
		http://wordnetcode.princeton.edu/wn3.1.dict.tar.gz; do \
		version=pwn`basename $$file | sed s/'[^0-9]'//g`; \
		if [ ! -e $$version ]; then mkdir $$version; fi; \
		if [ ! -e $$version/`basename $$file` ]; then \
			cd $$version;\
			wget $$file;\
			cd ..;\
		fi; \
	done;
	for dir in */; do \
		cd $$dir;\
		for file in *zip; do \
			unzip -u $$file;\
		done;\
		for file in *t*gz; do \
			tar -xvf $$file; \
		done; \
		cd ..; \
	done;
	for dir in */; do \
		for file in `find $$dir | grep -i dict | egrep -i '\.DAT|data\.'`; do \
			python3 dict2map.py $$file; \
		done > pwn`echo $$dir | sed s/'[^0-9]'//g`.tab;\
	done;





