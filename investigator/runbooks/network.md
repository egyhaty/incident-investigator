# Duplicate IP address and control-plane disconnects

## Recognize the pattern
Intermittent etcd connection reset, changing SSH host identities, API timeouts, and node readiness flapping can indicate a duplicate IP. Successful ping does not exclude an IP conflict. Compare the expected interface MAC with ARP responders for the affected address. Two distinct responders are strong evidence that two interfaces claim the address; verify ownership before remediation.

## Safe response
Use authoritative VM inventory to identify the conflicting interface. Isolate the unintended interface only after ownership is verified. Preserve its configuration. Do not stop the legitimate control-plane node. Refresh neighbor caches after removing the conflicting endpoint. Assign a verified unused address and correct persistent provisioning before reconnecting the isolated VM.

## Verify recovery
Repeat ARP observations, verify all etcd endpoints, check peer-reset logs, and confirm node readiness over time. A short successful health check is evidence of recovery, not proof that the fault cannot recur.
