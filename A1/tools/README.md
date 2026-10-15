# check_convention.py

Static MIPS calling-convention checker for `worms.s`. Not part of the submission.

    python3 A1/tools/check_convention.py A1/assignment1/worms.s            # your 14 functions
    python3 A1/tools/check_convention.py A1/assignment1/worms.s move fire  # chosen functions

It reports, per function:

- an `$s` register (or `$ra`, if the function calls something) that is written
  but not pushed, or pushes that are not mirrored by pops in reverse order;
- a `$t`, `$a` or `$v1` register read after a `jal` on some path without being
  written again first (the value would be undefined after the call).

It does not run the program, so it cannot check program logic, and it
only follows the register names it can see. Treat a clean result as "no
violations found", not as proof. `copy_bytes` and `print_three_digits` are
leaf helpers and are not in the default list; name them to check them.
