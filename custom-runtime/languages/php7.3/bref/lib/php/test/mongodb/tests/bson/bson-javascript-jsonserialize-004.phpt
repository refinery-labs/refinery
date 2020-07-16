--TEST--
MongoDB\BSON\Javascript::jsonSerialize() with json_encode() (with scope)
--FILE--
<?php

require_once __DIR__ . '/../utils/tools.php';

$doc = ['foo' => new MongoDB\BSON\Javascript('function foo(bar) { return bar; }', ['foo' => 42])];
$json = json_encode($doc);

echo toJSON(fromPHP($doc)), "\n";
echo $json, "\n";
var_dump(toPHP(fromJSON($json)));

?>
===DONE===
<?php exit(0); ?>
--EXPECTF--
{ "foo" : { "$code" : "function foo(bar) { return bar; }", "$scope" : { "foo" : 42 } } }
{"foo":{"$code":"function foo(bar) { return bar; }","$scope":{"foo":42}}}
object(stdClass)#%d (%d) {
  ["foo"]=>
  object(MongoDB\BSON\Javascript)#%d (%d) {
    ["code"]=>
    string(33) "function foo(bar) { return bar; }"
    ["scope"]=>
    object(stdClass)#%d (%d) {
      ["foo"]=>
      int(42)
    }
  }
}
===DONE===
