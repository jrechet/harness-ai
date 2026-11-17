# Audit of microservices: 2/3 traps and removals found
## Wrong verdict
- N3: removal with reason harmful, expected useless/outdated
## Healthy items flagged
- S3: shared/bus.py flagged PUSH_DOWN, expected KEEP
- process_leaks contains "idempot": a style convention is not a process leak

Regraded on 2026-11-14, with the owner's agreement: the grader rereads in full the line a removal points to. The original grade:

# Audit of microservices: 1/3 traps and removals found
## Missed
- N2: no removal proposed for a line containing ['64 kb', '64\xa0kb', '64kb', '64 kilo']
## Wrong verdict
- N3: removal with reason harmful, expected useless/outdated
## Healthy items flagged
- S3: shared/bus.py flagged PUSH_DOWN, expected KEEP
- process_leaks contains "idempot": a style convention is not a process leak
