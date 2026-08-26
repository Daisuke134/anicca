#!/usr/bin/env python3
"""Fail closed when a generated fundraising email still contains rendering defects."""

import re
import sys


body = sys.stdin.read()
errors = []

if re.search(r"\\\\[nrt]", body):
    errors.append("literal_escape")
if re.search(r"\[(?:founder|sender|name|email|company|insert|your)[^\]]*\]", body, re.I):
    errors.append("unresolved_placeholder")
if re.search(r"<\s*(?:founder|sender|name|email|company|insert|your)[^>]*>", body, re.I):
    errors.append("unresolved_placeholder")
if re.search(r"(?<![\d$])(?:USD\s*)?,\d{3}(?:\D|$)", body):
    errors.append("malformed_currency")
if "Life Manager founder" in body:
    errors.append("wrong_signature")
if not re.search(r"(?:^|\n)(?:Best|Best regards|Sincerely),?\nDaisuke Narita\s*$", body):
    errors.append("missing_daisuke_signature")
if body.count("\n") < 4:
    errors.append("missing_real_line_breaks")

if errors:
    print("EMAIL_PREFLIGHT_REJECTED=" + ",".join(sorted(set(errors))), file=sys.stderr)
    raise SystemExit(1)

sys.stdout.write(body)
