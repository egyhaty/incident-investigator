# Live connector plan

The current public demo is fixture-backed. The next integration is deliberately read-only and opt-in.

## Target cluster

The Karm DevOps repository documents the cluster API at `https://66.11.126.179:6443`. The investigator VM must reach that endpoint over an approved network path; the public dashboard must never expose the Kubernetes API or token.

## Access boundary

- dedicated Kubernetes ServiceAccount;
- namespace-scoped `Role`/`RoleBinding` wherever possible;
- `get`/`list` only for approved resources;
- no `create`, `update`, `patch`, `delete`, `exec`, port-forward, or arbitrary URL capability;
- token and CA bundle stored only on the VM, outside Git;
- Nginx remains the only public entry point;
- every live report labels its source as live and records the cluster identity.

## Implemented adapter

`investigator/connectors.py` contains the first narrow HTTPS adapter. It is disabled unless `INVESTIGATOR_K8S_API_URL` and `INVESTIGATOR_K8S_TOKEN` are explicitly configured. It accepts only three fixed observations: nodes, pods, and events.

## Remaining deployment work

1. Create and test the least-privilege ServiceAccount in the Karm DevOps cluster.
2. Install the token and CA file on the investigator VM with restrictive permissions.
3. Add a live evidence tool to the investigator allowlist and integration tests.
4. Run one complete incident from alert to report using live read-only observations.
5. Keep the CV unchanged until that run and the redesigned dashboard are verified.
