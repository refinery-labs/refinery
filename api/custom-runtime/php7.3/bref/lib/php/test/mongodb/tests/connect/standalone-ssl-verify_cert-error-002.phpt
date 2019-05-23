--TEST--
Connect to MongoDB with SSL and cert verification error (context options)
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_libmongoc_ssl(); ?>
<?php skip_if_not_ssl(); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

$driverOptions = [
    'context' => stream_context_create([
        'ssl' => [
            // libmongoc does not allow the hostname to be overridden as "server"
            'allow_invalid_hostname' => true,
            'allow_self_signed' => false, // "weak_cert_validation" alias
        ],
    ]),
];

echo throws(function() use ($driverOptions) {
    $manager = new MongoDB\Driver\Manager(URI, [], $driverOptions);
    $cursor = $manager->executeCommand(DATABASE_NAME, new MongoDB\Driver\Command(['ping' => 1]));
    var_dump($cursor->toArray()[0]);
}, 'MongoDB\Driver\Exception\ConnectionTimeoutException', 'executeCommand'), "\n";

?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
OK: Got MongoDB\Driver\Exception\ConnectionTimeoutException thrown from executeCommand
No suitable servers found (`serverSelectionTryOnce` set): [%s calling ismaster on '%s:%d']
===DONE===
