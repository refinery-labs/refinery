# The Backpack Parameter

For all `Code Blocks` in Refinery, there is a `main` function which takes two parameters. A code block input parameter, and a "backpack" parameter.

The following code demonstrates this in Python 2.7:

```python
def main(block_input, backpack):
    return "Hello World!"
```

The `backpack` parameter is a special object which allows you to store values across multiple block transitions. You can think of it as a place to store data while it passes along through the execution pipeline (thus, the name: backpack).

For example, say you have three blocks linked together: `[Block A]->[Block B]->[Block C]`. If you have the following code in `Block A`:

```python
def main(block_input, backpack):
    # Store some data in the backpack for later
    backpack["unique-key"] = "A value I'll need later!"
    return False
```

Then you will be able to access the value set in `unique-key` in both `Block B` and `Block C` via the backpack parameter.

This is useful for making your `Code Blocks` more re-usable because you don't have to constantly return every value to keep it around. Instead you can just return the data immediately needed for the next block in the pipeline and just stuff the rest in the backpack for later use.

!!! note
	Python, Node, and PHP all implement this in a magical way that allows you just to set a value on an object. In Go however, this is not the case due to it's strict nature and so you have to always return the backpack explicitly. See the default Go code in the Refinery editor for an example of this.