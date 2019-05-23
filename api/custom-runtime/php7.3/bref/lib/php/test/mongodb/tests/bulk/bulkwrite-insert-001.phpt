--TEST--
MongoDB\Driver\BulkWrite::insert() should always encode __pclass for Persistable objects
--SKIPIF--
<?php require __DIR__ . "/../utils/basic-skipif.inc"; ?>
<?php skip_if_not_live(); ?>
<?php skip_if_not_clean(); ?>
--FILE--
<?php
require_once __DIR__ . "/../utils/basic.inc";

class MyClass implements MongoDB\BSON\Persistable
{
    private $id;
    private $child;

    public function __construct($id, MyClass $child = null)
    {
        $this->id = $id;
        $this->child = $child;
    }

    public function bsonSerialize()
    {
        return [
            '_id' => $this->id,
            'child' => $this->child,
        ];
    }

    public function bsonUnserialize(array $data)
    {
        $this->id = $data['_id'];
        $this->child = $data['child'];
    }
}

$manager = new MongoDB\Driver\Manager(URI);

$bulk = new MongoDB\Driver\BulkWrite();
$bulk->insert(new MyClass('foo', new MyClass('bar', new MyClass('baz'))));
$result = $manager->executeBulkWrite(NS, $bulk);
printf("Inserted %d document(s)\n", $result->getInsertedCount());

$cursor = $manager->executeQuery(NS, new MongoDB\Driver\Query([]));
var_dump($cursor->toArray());

?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
Inserted 1 document(s)
array(1) {
  [0]=>
  object(MyClass)#%d (%d) {
    ["id":"MyClass":private]=>
    string(3) "foo"
    ["child":"MyClass":private]=>
    object(MyClass)#%d (%d) {
      ["id":"MyClass":private]=>
      string(3) "bar"
      ["child":"MyClass":private]=>
      object(MyClass)#%d (%d) {
        ["id":"MyClass":private]=>
        string(3) "baz"
        ["child":"MyClass":private]=>
        NULL
      }
    }
  }
}
===DONE===
