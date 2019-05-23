--TEST--
MongoDB\Driver\Cursor destruct should kill a live cursor
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_live(); ?>
<?php skip_if_not_clean(); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

function getNumOpenCursors(MongoDB\Driver\Manager $manager)
{
    $cursor = $manager->executeCommand(DATABASE_NAME, new MongoDB\Driver\Command(array('serverStatus' => 1)));
    $result = current($cursor->toArray());
    if (isset($result->metrics->cursor->open->total)) {
        return $result->metrics->cursor->open->total;
    }

    if (isset($result->cursors->totalOpen)) {
        return $result->cursors->totalOpen;
    }

    throw new RuntimeException('Could not find number of open cursors in serverStatus');
}

$manager = new MongoDB\Driver\Manager(URI);

$bulk = new MongoDB\Driver\BulkWrite();
$bulk->insert(array('_id' => 1));
$bulk->insert(array('_id' => 2));
$bulk->insert(array('_id' => 3));
$manager->executeBulkWrite(NS, $bulk);

$numOpenCursorsBeforeQuery = getNumOpenCursors($manager);

$cursor = $manager->executeQuery(NS, new MongoDB\Driver\Query(array(), array('batchSize' => 2)));

var_dump($cursor->isDead());
var_dump(getNumOpenCursors($manager) == $numOpenCursorsBeforeQuery + 1);

unset($cursor);

var_dump(getNumOpenCursors($manager) == $numOpenCursorsBeforeQuery);

?>
===DONE===
<?php exit(0); ?>
--EXPECT--
bool(false)
bool(true)
bool(true)
===DONE===
