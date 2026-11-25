# Build the five 2D C solvers.
#
# Linux:   make -C solvers
# Windows: make -C solvers          (MSYS2/MinGW-w64 shell, adds .exe + -static)
#          .\solvers\build_windows.ps1
#
# The sources define `printf` as `__mingw_printf` only when `_WIN32` is set,
# because MinGW's standard printf does not handle long double correctly.

CC      ?= gcc
CFLAGS  ?= -O2
LDLIBS  ?= -lm

# GNU make predefines CC=cc; prefer gcc unless the user overrides it.
ifeq ($(origin CC),default)
CC := gcc
endif

RUNNERS := runners
SOLVERS := NTS_DD NTS_LD NTS_STEP NTS_RM_CN NTS_RM_LLN

ifeq ($(OS),Windows_NT)
EXE      := .exe
LDFLAGS += -static
endif

BINS := $(addprefix $(RUNNERS)/,$(addsuffix $(EXE),$(SOLVERS)))

.PHONY: all rebuild clean test

all: $(BINS)

rebuild: clean all

$(RUNNERS)/%$(EXE): $(RUNNERS)/%.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

clean:
	rm -f $(addprefix $(RUNNERS)/,$(addsuffix $(EXE),$(SOLVERS)))

test: all
	cd .. && uv run python -m cli.run_tests -p "test_2d_solvers.py"
