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
  host="docker@192.168.99.102",
  targetdir="/home/docker/refinery",
  exclude = {
    "/.idea",
    "/.git",
  },
  ssh = {
    -- Replace the path of this key with your docker-machine key (substitute machine4 probably)
    identityFile = "~/.docker/machine/machines/machine4/id_rsa",
  }
}

