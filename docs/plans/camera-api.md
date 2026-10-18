# Camera API override

1. Inspect CLI, Docker wiring, protocol handling, and tests.
2. Add auto/legacy/modern selection while preserving downstream protocol behavior.
3. Verify CLI, shell startup, parsing, and downloads; run existing suites.
4. Document options, versioned image build, Portainer update, and rollback.

Implementation, tests, and deployment preparation are complete. All 185 pytest cases and both protocol behavioral suites passed; applicable pre-commit checks passed. Docker build/container integration remains unverified because the local Docker daemon is unavailable.

Deployment is excluded until explicitly approved.
