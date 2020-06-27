--TEST--
MongoDB\Driver\Session::advanceOperationTime() with TimestampInterface
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_libmongoc_crypto(); ?>
<?php skip_if_not_replica_set(); ?>
<?php skip_if_server_version('<', '3.6'); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

class MyTimestamp implements MongoDB\BSON\TimestampInterface
{
    public function getIncrement()
    {
        return 5678;
    }

    public function getTimestamp()
    {
        return 1234;
    }

    public function __toString()
    {
        return sprintf('[%d:%d]', $this->getIncrement(), $this->getTimestamp());
    }
}

$manager = new MongoDB\Driver\Manager(URI);
$session = $manager->startSession();

echo "Initial operation time of session:\n";
var_dump($session->getOperationTime());

$session->advanceOperationTime(new MyTimestamp);

echo "\nOperation time after advancing session:\n";
var_dump($session->getOperationTime());

?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
Initial operation time of session:
NULL

Operation time after advancing session:
object(MongoDB\BSON\Timestamp)#%d (%d) {
  ["increment"]=>
  string(4) "5678"
  ["timestamp"]=>
  string(4) "1234"
}
===DONE===
