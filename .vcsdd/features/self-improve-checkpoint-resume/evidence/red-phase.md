new-feature-tests: FAIL (pre-implementation, confirmed via git stash of run_evolve.sh + lib/checkpoint_resume.py)
regression-baseline: PASS

=== RED (stashed impl, tests only) ===
1 collection error (ImportError: cannot import name checkpoint_resume) blocking test_checkpoint_resume.py's 23 tests
test_checkpoint_resume_wiring.py: 7 failed, 1 passed (PROP-CR-WIRE1/2/2b/3x2/13/LIVE1 all failed as expected pre-wiring)
