# SPDX-License-Identifier: GPL-2.0-only
obj-m += cdc_ncm.o

KVERSION ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KVERSION)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -rf *.o *.ko *.mod.c *.mod *.symvers *.order .*.cmd .tmp_versions

install:
	./install.sh

uninstall:
	./uninstall.sh

.PHONY: all clean install uninstall
