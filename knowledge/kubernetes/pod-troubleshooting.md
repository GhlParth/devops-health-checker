# Kubernetes Pod Troubleshooting

## CrashLoopBackOff

CrashLoopBackOff means Kubernetes repeatedly starts a container and the
container exits.

Common causes include:

- Application process crashes during startup
- Missing environment variables
- Incorrect configuration
- Missing Kubernetes Secret
- Missing ConfigMap
- Application cannot connect to a dependency
- Incorrect command or entrypoint
- Insufficient permissions
- Resource limits causing the container to terminate

## First Checks

Check the pod:

kubectl get pod <pod-name> -n <namespace>

Describe the pod:

kubectl describe pod <pod-name> -n <namespace>

Check current logs:

kubectl logs <pod-name> -n <namespace>

Check logs from the previous container:

kubectl logs <pod-name> -n <namespace> --previous

Check pod events:

kubectl get events -n <namespace> --sort-by=.lastTimestamp

## Investigation Process

1. Check the pod status.
2. Check container restart count.
3. Inspect pod events.
4. Inspect current logs.
5. Inspect previous container logs.
6. Check ConfigMaps and Secrets.
7. Check application dependencies.
8. Check CPU and memory configuration.
9. Verify probes.
10. Confirm the deployment configuration.

## OOMKilled

OOMKilled indicates that a container was terminated because it exceeded
its available memory limit.

Check:

kubectl describe pod <pod-name> -n <namespace>

Look for:

Reason: OOMKilled

If confirmed, investigate:

- Container memory limit
- Application memory usage
- Memory leak
- Workload traffic
- JVM or runtime memory configuration

Do not immediately increase memory limits without understanding the
application's memory behavior.