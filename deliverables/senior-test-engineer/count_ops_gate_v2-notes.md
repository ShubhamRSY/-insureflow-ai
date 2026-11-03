# count_ops_gate_v2.py — reading notes (the script is frozen, sha256 a57010b0…3085a, D-141)

## M1 rule (D-158, @user, 2026-11-03; memo T-121 M1)
- An in-scope gold file that the pipeline sent to **manual intake** is a **scope miss** (false manual intake), counted under the P-055 scope gate. It is **not** a C2 operations silent error: no operations value was shown.
- C2 (silent = 0) is counted only over in-scope files that reached a status other than manual intake. C4 is unchanged (present >= 18/20 and hits >= 15/20 over all 20; a manual-intake file is not present); the number of false-manual-intake files is reported next to it.
- The frozen script still prints its own rows; the write-up applies this rule on top and lists each manual-intake file as "scope miss, not counted in C2". The script is not edited and T-121 is not re-scored (D-020).
- Applies from the next hold-out (T-128). Set before any T-128 gold exists.
