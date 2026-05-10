#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 A1 worker fixture: writes isatty=<bool> to stdout."""

import sys

sys.stdout.write("isatty=" + str(sys.stdin.isatty()))
sys.stdout.flush()
