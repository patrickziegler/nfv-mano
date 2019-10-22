BINDIR := build/
BIN := \
test_bitfield

all: $(BIN)
	@echo "Done"

clean:
	$(RM) -r ${BINDIR}

%: %.c
	mkdir -p ${BINDIR}
	${CC} $< -o $(addprefix $(BINDIR),$@)
