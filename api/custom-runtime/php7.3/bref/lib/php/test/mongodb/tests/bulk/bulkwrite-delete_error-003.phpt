--TEST--
MongoDB\Driver\BulkWrite::delete() with BSON encoding error (null bytes in keys)
--FILE--
<?php

require_once __DIR__ . '/../utils/tools.php';

$bulk = new MongoDB\Driver\BulkWrite;

echo throws(function() use ($bulk) {
    $bulk->delete(["\0" => 1]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n\n";

echo throws(function() use ($bulk) {
    $bulk->delete(["x\0" => 1]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n\n";

echo throws(function() use ($bulk) {
    $bulk->delete(["\0\0\0" => 1]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n\n";

echo throws(function() use ($bulk) {
    $bulk->delete(['x' => 1], ['collation' => ["\0" => 1]]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n\n";

echo throws(function() use ($bulk) {
    $bulk->delete(['x' => 1], ['collation' => ["x\0" => 1]]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n\n";

echo throws(function() use ($bulk) {
    $bulk->delete(['x' => 1], ['collation' => ["\0\0\0" => 1]]);
}, 'MongoDB\Driver\Exception\UnexpectedValueException'), "\n";

?>
===DONE===
<?php exit(0); ?>
--EXPECT--
OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "".

OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "x".

OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "".

OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "".

OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "x".

OK: Got MongoDB\Driver\Exception\UnexpectedValueException
BSON keys cannot contain null bytes. Unexpected null byte after "".
===DONE===
