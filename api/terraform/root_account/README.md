# Root Account Terraform

Setup Refinery's infra

## Getting refinery_root_organization_id

```
➜  aws organizations list-roots
{
    "Roots": [
        {
            "Id": "r-83fi",
            "Arn": "arn:aws:organizations::836052632342:root/o-kajworae0m/r-83fi",
            "Name": "Root",
            "PolicyTypes": []
        }
    ]
}

```

We want `o-kajworae0m/r-83fi` to use as the variable `refinery_root_organization_id`
