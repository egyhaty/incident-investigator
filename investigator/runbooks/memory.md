# OOMKilled and container memory limits

## Recognize the pattern
For a restarting application, inspect last termination reason, restart count, memory limit, and recent usage. OOMKilled with usage close to the container memory limit supports a container memory limit diagnosis. Exit code 137 alone is not enough to prove an out-of-memory kill. A node with free memory can still host a container that hits its own limit.

## Safe response
Profile the application for leaks or unexpected workload growth. Compare the memory request and limit with representative usage and node capacity. Propose a justified limit adjustment and a controlled rollout. Do not increase VM memory blindly or remove container limits.

## Verify recovery
Check application readiness and restart counts through a representative load period. A successful restart without representative load does not demonstrate a durable fix.
