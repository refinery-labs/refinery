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

### What are Transitions?

In Refinery [transitions](/transitions/) indicate the path that an execution flow will take once deployed. This means that once deployed, if the `Hello Block` is executed the `World Block` will be executed afterwards (assuming no exception occurs while running `Hello Block`). The data returned from the `Hello Block` will automatically be passed as input to the `World Block` (e.g. the `block_input` parameter in `main()`). Note that blocks in the `Editor` tab which we are currently using will not trigger other blocks until they are deployed. This allows you to modify and iterate on your Refinery `Code Blocks` without triggering the entire execution flow.

In our specific case, this means that the `World!` string returned from the `Hello Block` block:

```python
# Code in Hello Code Block
def main(block_input, backpack):
    print( "Hello" )
    return "World!"
```

Will be passed as input to the `World Block`:

```python
# Code in World Code Block
def main(block_input, backpack):
    print( block_input )
    return False
```

Note that even though this example uses Python for both `Code Blocks`, you can pass data between `Code Blocks` of any language type! You can return data from a Node 8.10 `Code Block` to a Go 1.12 `Code Block` and it will work the same way. This is a fairly interesting property because it means you can import `Code Blocks` into your project in a language you don't write and still use them for your Refinery project.

!!! note
	It's important to note that you can only return [JSON-serializable data](https://restfulapi.net/json-data-types/). This means simple data types like `integers`, `strings`, `arrays` and simple `objects` are all perfectly fine to pass between `Code Blocks`. This restriction allows the ability to pass data between multiple languages, but does restrict what types of data can be passed around.
	
## Scheduling a Continually-Executing Job

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/adding-timer-block.webm" type="video/webm" />
	<source src="/getting-started/media/adding-timer-block.mp4" type="video/mp4" />
</video>

Let's make our project a job which will execute every minute! Click on the `Add Block` button again and select the `Timer Block` from the menu. Modify the `Block Name` field to be `Every Minute` and change the `Schedule Expression` to be `rate(1 minutes)` instead of `rate(2 minutes)`. Finally, add a transition from the `Timer Block` to the `Hello Block`.

We've now made our project into a continually-executing job which will execute every minute once we've deployed it. Unlikely conventional server-based architecture, jobs deployed on Refinery require significantly less maintenance. You never have to perform system maintenance on the servers executing your job. Additionally you are charged purely for the compute and resources used to execute the job (instead of paying for an idling VPS or dedicated server, for example).

## Deploying the Project

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/deploying-the-project.webm" type="video/webm" />
	<source src="/getting-started/media/deploying-the-project.mp4" type="video/mp4" />
</video>

You can now deploy your project by clicking the `Deploy Project` button on the left-side of the page and confirming the action by clicking the `Confirm Deploy` button.

Once you've done this you've successfully deployed your first Refinery project, pat yourself on the back!

If you wait sixty seconds you will see your first scheduled job execute. This brings us to the next topic of discussion...

## Deployed Project Logging & Debugging

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/debugger-deployment.webm" type="video/webm" />
	<source src="/getting-started/media/debugger-deployment.mp4" type="video/mp4" />
</video>

Once you've deployed a project the `Block Executions` pane will automatically open. You can also manually open the panel by clicking the `Block Executions` button on the left side of the page.

The `Block Executions` panel shows a list of executions which have occurred for this deployment. These executions are grouped into "execution pipelines", which means that you can follow a chain of executions from the start to the end of the chain. This allows you to follow the flow of execution in your deployed service and better understand the chain of events that led to a particular error or bug.

Once you select a given execution pipeline from the list you'll see that the `Code Blocks` are marked as successful <img src="/debugging/images/code-block-success.png" style="width: 25px; height: 25px;" /> or unsuccessful <img src="/debugging/images/code-block-error.png" style="width: 25px; height: 25px;" />. These indicate whether or not your `Code Block` encountered an uncaught exception or if it executed successfully without issue.

By default Refinery logs the full input data, return data, and program terminal output. This is to allow for easy reproducibility of bugs by allowing for replaying the `Code Block` input in the `Editor` tab to trigger the bug as it occurred in the deployment.

For ongoing executions the `Code Blocks` will automatically update as the execution continues.

If you'd like to learn more about what Refinery logs and how to better debug your deployed project, see the [Debugging & Logging documentation](/debugging/).

## Tearing Down Your Deployment

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/getting-started/media/destroying-deployment.webm" type="video/webm" />
	<source src="/getting-started/media/destroying-deployment.mp4" type="video/mp4" />
</video>

Although it has been fun, you probably don't want to run the Hello World project forever. You can tear down your deployment by clicking on the `Destroy Deploy` button on the left-side of the page. This will take down your deployment and bring you back to the `Editor` tab. You can then make changes in the `Editor` and deploy them all over again!

## Going Forward

Now that you've deployed your first project on Refinery, why not try something a bit more complicated?

* [Learn about Debugging & Logging a deployed project](/debugging/)
* [Learn about the "backpack" parameter (carrying data across block executions)](/backpack/)
* [Learn about the different Refinery Transition types.](/transitions/)
* [Learn about the different Refinery Block types.](/blocks/)
* [Learn about making an API Endpoint in Refinery.](/tutorials/api-endpoints/)
