# Audit of django-mvc: 10/10 traps and removals found · ok


Regraded on 2026-11-14, with the owner's agreement: the grader rereads in full the line a removal points to, and the answer key targets the "bulk e-mails" half of the rule, not the `post_save` half, guarded by a test. The original note:

# Audit of django-mvc: 10/10 traps and removals found
## Healthy items flagged
- guarded_rules declares "No e-mail in a post_save signal nor in save()" guarded by enrollments/tests/test_services.py:106-112 (test job of .github/workflows/ci.yml): nothing verifies it (bulk e-mails: review only)
