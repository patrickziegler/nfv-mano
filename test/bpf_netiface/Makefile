BIN := \
test_get_mac

LDFLAGS := \
-luuid

all: $(BIN)
	@echo "Done"

clean:
	$(RM) -f $(addprefix $(BINDIR),$(BIN))

%: %.c
	${CC} $< -o $@ $(LDFLAGS)
