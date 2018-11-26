# Kube Deploy Verify

## Usage

Example:

```bash
name="my-deploy"
if ! python36 -u bin/verify.py "$name"; then
  echo "ROLLING-BACK DEPLOYMENT!"
  kubectl rollout undo deployment "$name"
  exit 1
fi
```
