settings {
  logfile = "/tmp/lsyncd.log",
  statusFile = "/tmp/lsyncd-status.log",
  statusInterval = 1,
}

sync {
  default.rsyncssh,
  delay = 1,
  source="../../",
  -- Replace this host with your docker-machine host
  host="ubuntu@54.202.75.48",
  targetdir="/home/ubuntu/refinery",
  exclude = {
    "/.idea",
    "/.git",
  },
  ssh = {
    -- Replace the path of this key with your docker-machine key (substitute machine4 probably)
    identityFile = "~/.docker/machine/machines/aws-machine/id_rsa",
  }
}

