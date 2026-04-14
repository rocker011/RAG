# Debug Scripts

This directory stores one-off debugging and recovery scripts.

## Rule

If a script is:

- tied to a specific dataset
- used for troubleshooting a failed run
- not part of the standard experiment pipeline

then it should live under:

- `evaluation/debug/<dataset>/`

## Current example

- `hypertension/run_step1_debug.py`
