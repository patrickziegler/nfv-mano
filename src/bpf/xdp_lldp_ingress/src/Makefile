LIBCLANG ?= /usr/lib64/clang/9.0.0
CLANG    ?= /usr/bin/clang
LLC      ?= /usr/bin/llc
ARCH     ?= $(subst x86_64,x86,$(shell arch))

PROJECT_DIR  := ../

KDIR   ?= $(PROJECT_DIR)../../../extern/linux
BPFDIR ?= $(KDIR)/tools/lib/bpf
BPFLIB ?= $(BPFDIR)/libbpf.a
BINDIR ?= $(PROJECT_DIR)build/

BIN := \
xdp_lldp_ingress_kern.o \
xdp_lldp_ingress_user

CFLAGS_KERN := \
-nostdinc \
-I$(PROJECT_DIR)../bpf_common/include \
-I$(KDIR)/include \
-I$(KDIR)/include/uapi \
-I$(KDIR)/arch/$(ARCH)/include \
-I$(KDIR)/arch/$(ARCH)/include/uapi \
-I$(KDIR)/arch/$(ARCH)/include/generated \
-I$(KDIR)/arch/$(ARCH)/include/generated/uapi \
-include $(KDIR)/include/linux/kconfig.h \
-include $(KDIR)/samples/bpf/asm_goto_workaround.h \
-I$(KDIR)/tools/testing/selftests/bpf \
-I$(KDIR)/tools/lib/bpf \
-I$(LIBCLANG)/include \
-D__KERNEL__ \
-Wno-pointer-sign \
-Wno-address-of-packed-member \
-emit-llvm \
-O2 \
-g

LFLAGS_KERN := \
-march=bpf \
-mcpu=$(CPU) \
-filetype=obj

CFLAGS_USER := \
-I$(KDIR)/tools/lib \
-O2

LFLAGS_USER := \
-L$(KDIR)/tools/lib/bpf \
-Wl,-Bstatic -lbpf -Wl,-Bdynamic \
-lelf

all: $(BIN)
	@echo "Done"

clean:
	$(RM) -f $(addprefix $(BINDIR),$(BIN))

$(BINDIR):
	mkdir -p $(BINDIR)

$(BPFLIB):
	$(MAKE) -C $(BPFDIR) OUTPUT=$(BPFDIR) /

%_kern.o: %_kern.c $(BINDIR)
	$(CLANG) $(CFLAGS_KERN) -c $< -o - | \
	$(LLC) $(LFLAGS_KERN) -o $(BINDIR)$@

%_user: %_user.c $(BPFLIB) $(BINDIR)
	$(CLANG) $(CFLAGS_USER) $< $(LFLAGS_USER) -o $(BINDIR)$@
