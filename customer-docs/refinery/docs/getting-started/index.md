# Getting Started - Creating Your First Refinery Project

This tutorial will walk you through how to make your first Refinery project. While the first project is a simple one it will help you better understand some of Refinery's features, as well as getting a general feel for the designer.

## Creating a New Project

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/creating-a-project.webm" type="video/webm" />
	<source src="/getting-started/media/creating-a-project.mp4" type="video/mp4" />
</video>

First thing to do is to create a new project. Navigate to the [projects page](https://app.refinery.io/projects), type your desired project name in the `Project Name` field, and click `Create Project`! Once you've done this you now have a blank canvas ready for your next creation.

## Adding Your First Block

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/creating-hello-block.webm" type="video/webm" />
	<source src="/getting-started/media/creating-hello-block.mp4" type="video/mp4" />
</video>

Let's add our first block to the new project, click the `Add Block` button on the left-side of the page. Select the `Code Block` option from the menu and a new [`Code Block`](/blocks/#code-block) will be added to your project. To better keep track of what is what, rename the `Block Name` to `Hello Block` (or whatever you prefer).

Then, edit the code to be the following Python code:

```python
def main(block_input, backpack):
    print( "Hello" )
    return "World!"

```

!!! note
	Refinery supports more languages than just Python! Currently support includes Go 1.12, Node 8.10, and PHP 7.3 as well. You can change the language the `Code Block` uses by changing the drop-down option under the `Block Runtime` section of the `Edit Block` pane.
	
## Adding Your Second Block

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/creating-world-block.webm" type="video/webm" />
	<source src="/getting-started/media/creating-world-block.mp4" type="video/mp4" />
</video>

What is `Hello` without `World`? Add a second block to your new project by again clicking on the `Add Block` button on the left-side of the page. With this `Code Block` set the name to `World Block` and the code to the following:

```python

def main(block_input, backpack):
    print( block_input )
    return False
```

The above code just prints the input passed to the `Code Block`. We now have two `Code Blocks` but the magic comes in connecting blocks together in the editor.

## Connecting the Blocks

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/connecting-hello-and-world.webm" type="video/webm" />
	<source src="/getting-started/media/connecting-hello-and-world.mp4" type="video/mp4" />
</video>

Click on the `Hello Block` to select it and then click the `Add Transition` button on the left side of the page. Select the `then` transition from the presented menu. You will see that the `World Block` begins to flash indicating that you can transition to it from the currently-selected `Hello Block`. Click on the `World Block` to create the transition.