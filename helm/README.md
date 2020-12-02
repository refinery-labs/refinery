# Refinery Helm Charts

```
helm install \
    --set server.replicaCount=1 \
    --set cassandra.config.cluster_size=1 \
    --set prometheus.enabled=false \
    --set grafana.enabled=false \
    --set elasticsearch.enabled=false \
    --set kafka.enabled=false \
		--create-namespace --namespace temporal \
    temporal helm-charts/ --timeout 15m
helm install --namespace refinery --create-namespace refinery refinery/
```

## AWS Codebuild permissions

The CodeBuild process needs to be able to access the Kubernetes cluster. To do so, modify the `aws-auth` configMap with the command `kubectl edit -n kube-system configmap/aws-auth` and add the following lines below the `mapUsers` key:
```

- userarn: arn:aws:iam::<AWS_ACCOUNT_ID>:role/<ROLE_NAME>
  username: <ROLE_NAME>
  groups:
    - system:masters
```

The role is the role that is attached to the CodeBuild job.
