# Refinery Project running in Temporal Test

## Setup

### Temporal

#### Run the following commands
```
git clone https://github.com/temporalio/temporal.git
cd temporal
curl -L https://github.com/temporalio/temporal/releases/latest/download/docker.tar.gz | tar -xz --strip-components 1 docker/docker-compose.yml
make bins
docker-compose up
```

#### Run the following commands in a separate terminal
```
./tctl --ns refinery n re --gd false
```

### Workflow Manager
```
# In first terminal...
cd worker

# Configure secrets
cp config/secrets.example.yaml config/secrets.yaml
# Using an editor, set the secret values to the root Refinery account's cli creds

go run .

# In second terminal...
cd workflowmanager
go run .

# In third terminal...
ngrok http 3000
```

### Configuring API server to use Workflow Manager
Take the ngrok url, append `/api/v1` (ex. `https://1234.ngrok.io/api/v1`), and place it under `workflow_manager_api_url` in the config.
