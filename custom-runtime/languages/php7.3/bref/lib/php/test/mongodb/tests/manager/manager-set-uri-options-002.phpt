--TEST--
MongoDB\Driver\Manager: Connecting to MongoDB using "ssl" from $options
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_libmongoc_ssl(); ?>
<?php skip_if_not_ssl(); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

$opts = array(
    "ssl" => array(
        "verify_peer" => false,
        "verify_peer_name" => false,
        "allow_self_signed" => true,
    ),
);
$context = stream_context_create($opts);

$options = array(
    "ssl" => false,
    "serverselectiontimeoutms" => 100,
);
/* The server requires SSL */
$manager = new MongoDB\Driver\Manager(URI, $options, array("context" => $context));

$bulk = new MongoDB\Driver\BulkWrite;
$bulk->insert(array("my" => "value"));
echo throws(function() use ($manager, $bulk) {
    $inserted = $manager->executeBulkWrite(NS, $bulk)->getInsertedCount();
    printf("Inserted incorrectly: %d\n", $inserted);
}, "MongoDB\Driver\Exception\ConnectionTimeoutException"), "\n";



$options = array(
    "ssl" => true,
);
$manager = new MongoDB\Driver\Manager(URI, $options, array("context" => $context));
$bulk = new MongoDB\Driver\BulkWrite;

$bulk->insert(array("my" => "value"));
$inserted = $manager->executeBulkWrite(NS, $bulk)->getInsertedCount();
printf("Inserted: %d\n", $inserted);
?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
OK: Got MongoDB\Driver\Exception\ConnectionTimeoutException
No suitable servers found (`serverSelectionTryOnce` set): [%scalling ismaster on '%s']
Inserted: 1
===DONE===
