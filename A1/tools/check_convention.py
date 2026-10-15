#!/usr/bin/env python3
"""Static MIPS calling-convention checker for worms.s (not part of the submission).

Usage:  python3 check_convention.py worms.s [function ...]

For every function it checks that
  1. every $s register (and $ra, if the function calls anything) that the
     function writes is pushed in the prologue and popped in reverse order;
  2. on every path, no caller-saved register ($t0-$t9, $a0-$a3, $v1) is read
     after a `jal` unless it was written again since that call.
With no function names given, only the assignment functions you write are checked.
"""
import re
import sys

MINE = ("main in_bounds get_input play render_background game_over aim render_worms "
        "overlaps_with_terrain move render_projectile fire render_end_screen print_rgb").split()
CALLER_SAVED = {f"$t{i}" for i in range(10)} | {f"$a{i}" for i in range(4)} | {"$v1"}
REG = re.compile(r"\$[a-z0-9]+")
NO_DEST = ("sw", "sb", "push", "jr", "b", "j", "jal", "syscall")


def functions(text):
    """Split the file into {name: [(label_or_None, instruction_text, lineno)]}."""
    funcs, cur, name = {}, [], None
    for no, raw in enumerate(text.split("\n"), 1):
        m = re.match(r"# \.TEXT <(\w+)>", raw)
        if m:
            name, funcs[name] = m.group(1), []
            continue
        code = raw.split("#")[0].strip().replace("\t", " ")
        if name is None or not code or code.startswith("."):
            continue
        while re.match(r"^\w+:", code):
            label, code = code.split(":", 1)
            funcs[name].append((label, None, no))
            code = code.strip()
        if code:
            funcs[name].append((None, code, no))
    return funcs


def reads_writes(ins):
    op, _, rest = ins.replace("\t", " ").partition(" ")
    regs = REG.findall(rest)
    if op == "pop":
        return [], regs
    if op in NO_DEST or op.startswith(("beq", "bne", "bl", "bg", "bn")):
        return regs, []
    return regs[1:], regs[:1]            # dest-first instruction


def check(name, body):
    problems = []
    inss = [(i, ins, no) for i, (lab, ins, no) in enumerate(body) if ins]
    labels = {lab: i for i, (lab, ins, no) in enumerate(body) if lab}
    # 1. saved registers
    pushed = [REG.findall(ins)[0] for _, ins, _ in inss if ins.startswith("push")]
    popped = [REG.findall(ins)[0] for _, ins, _ in inss if ins.startswith("pop")]
    need = {w for _, ins, _ in inss for w in reads_writes(ins)[1] if w.startswith("$s") and w != "$sp"}
    if any(ins.startswith("jal") for _, ins, _ in inss):
        need.add("$ra")
    if set(pushed) != need:
        problems.append(f"saved {sorted(pushed)} but should save {sorted(need)}")
    if pushed != popped[::-1]:
        problems.append(f"pushes {pushed} are not mirrored by pops {popped}")
    # 2. caller-saved registers read after a call (forward dataflow, may-analysis)
    state = {0: frozenset()}
    work = [0]
    while work:
        i = work.pop()
        poisoned = set(state[i])
        lab, ins, no = body[i]
        succ = []
        if ins:
            reads, writes = reads_writes(ins)
            for r in reads:
                if r in poisoned:
                    problems.append(f"line {no}: `{ins}` reads {r} after a call clobbered it")
            poisoned -= set(writes)
            op = ins.split()[0]
            if op == "jal":
                poisoned |= CALLER_SAVED
                poisoned.discard("$v0")
            target = REG.sub("", ins).split()[-1] if ins.split()[0] in ("b", "j") or ins.split()[0].startswith(("beq", "bne", "bl", "bg", "bn")) else None
            if target in labels:
                succ.append(labels[target])
            if op not in ("b", "j", "jr"):
                succ.append(i + 1)
        else:
            succ.append(i + 1)
        for s in succ:
            if s < len(body):
                new = state.get(s, frozenset()) | frozenset(poisoned)
                if s not in state or new != state[s]:
                    state[s] = new
                    work.append(s)
    return sorted(set(problems))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "worms.s"
    wanted = sys.argv[2:] or MINE
    funcs = functions(open(path).read())
    bad = 0
    for name in wanted:
        if name not in funcs:
            print(f"{name:24} NOT FOUND")
            bad += 1
            continue
        problems = check(name, funcs[name])
        print(f"{name:24} {'OK' if not problems else 'PROBLEM'}")
        for p in problems:
            print(f"    - {p}")
        bad += bool(problems)
    sys.exit(1 if bad else 0)


main()
