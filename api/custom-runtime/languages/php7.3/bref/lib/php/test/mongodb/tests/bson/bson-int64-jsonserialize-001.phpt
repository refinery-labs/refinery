--TEST--
MongoDB\BSON\Int64::jsonSerialize() return value
--FILE--
<?php

$tests = [
    unserialize('C:18:"MongoDB\BSON\Int64":47:{a:1:{s:7:"integer";s:19:"9223372036854775807";}}'),
    unserialize('C:18:"MongoDB\BSON\Int64":48:{a:1:{s:7:"integer";s:20:"-9223372036854775808";}}'),
    unserialize('C:18:"MongoDB\BSON\Int64":28:{a:1:{s:7:"integer";s:1:"0";}}'),
];

foreach ($tests as $test) {
    var_dump($test->jsonSerialize());
}

?>
===DONE===
<?php exit(0); ?>
--EXPECT--
array(1) {
  ["$numberLong"]=>
  string(19) "9223372036854775807"
}
array(1) {
  ["$numberLong"]=>
  string(20) "-9223372036854775808"
}
array(1) {
  ["$numberLong"]=>
  string(1) "0"
}
===DONE===
