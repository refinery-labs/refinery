
"""
Example input:
{
  "ImageSizeInBytes": "374340357",
  "ImageDigest": "sha256:93a44537ed51c8aa634476b0a39f836b73e8ad027bde78b95077993fe527d161",
  "Version": "1.0",
  "ImagePushedAt": "Thu Aug 06 20:16:27 UTC 2020",
  "RegistryId": "134071937287",
  "RepositoryName": "pidgeon-server-prod",
  "ImageURI": "134071937287.dkr.ecr.us-west-2.amazonaws.com/pidgeon-server-prod@sha256:93a44537ed51c8aa634476b0a39f836b73e8ad027bde78b95077993fe527d161",
  "ImageTags": [
    "23dfae6",
    "latest"
  ]
}
"""

def main(event, context):
    return """
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "134071937287.dkr.ecr.us-west-2.amazonaws.com/pidgeon-server-prod:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "HostPort": "8080",
      "ContainerPort": "8080"
    }
  ]
}
"""