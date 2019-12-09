BINDIR := build/
BIN := \
test_get_mac

all: $(BIN)
	@echo "Done"

clean:
	$(RM) -r ${BINDIR}

%: %.c
	mkdir -p ${BINDIR}
	${CC} $< -luuid -o $(addprefix $(BINDIR),$@)
