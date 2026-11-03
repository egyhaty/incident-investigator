# Replica scheduling and storage capacity

## Recognize the pattern
A disk can have free physical space while refusing new replicas. Compare provisioned replica capacity with the scheduling limit, reserved space, and actual usage. A false schedulable flag with provisioned capacity above the limit is a storage scheduling capacity problem, not automatically a full filesystem or a memory shortage.

## Safe response
Verify the hypervisor backing store has capacity. Identify the dedicated storage disk by serial and mounted filesystem. Plan an online disk and filesystem expansion where supported. Do not expand an unverified device, shrink a disk, delete replicas, or weaken the capacity policy merely to clear an alert. This investigator proposes actions; it does not perform them.

## Verify recovery
Confirm the guest filesystem sees the new size, every intended disk is schedulable, and attached volumes are healthy. Validate a fresh backup separately; capacity recovery alone does not prove backup recoverability.
