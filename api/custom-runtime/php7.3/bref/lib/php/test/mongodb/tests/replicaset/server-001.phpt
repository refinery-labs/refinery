--TEST--
MongoDB\Driver\Server: Manager->getServer() returning correct server
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_replica_set(); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

$manager = new MongoDB\Driver\Manager(URI);


$doc = array("example" => "document");
$bulk = new \MongoDB\Driver\BulkWrite();
$bulk->insert($doc);
$wresult = $manager->executeBulkWrite(NS, $bulk);

$bulk = new \MongoDB\Driver\BulkWrite();
$bulk->insert($doc);

/* writes go to the primary */
$server = $wresult->getServer();

var_dump(
    $server->getHost(),
    $server->getTags(),
    $server->getLatency(),
    $server->getPort(),
    $server->getType() == MongoDB\Driver\Server::TYPE_RS_PRIMARY,
    $server->isPrimary(),
    $server->isSecondary(),
    $server->isArbiter(),
    $server->isHidden(),
    $server->isPassive()
);
$info = $server->getInfo(); // isMaster output changes between mongod versions
var_dump($info["setName"], $info["hosts"]);
var_dump($info["me"] == $server->getHost() . ":" . $server->getPort());
?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
string(%d) "%s"
array(2) {
  ["dc"]=>
  string(2) "pa"
  ["ordinal"]=>
  string(3) "one"
}
int(%d)
int(%d)
bool(true)
bool(true)
bool(false)
bool(false)
bool(false)
bool(false)
string(%d) "REPLICASET%S"
array(2) {
  [0]=>
  string(%d) "%s:%d"
  [1]=>
  string(%d) "%s:%d"
}
bool(true)
===DONE===
