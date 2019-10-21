BIN := \
test_bitfield

all: $(BIN)
	@echo "Done"

clean:
	$(RM) -f $(addprefix $(BINDIR),$(BIN))

%: %.c
	${CC} $< -o $@
