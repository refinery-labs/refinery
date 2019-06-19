# Getting Started

This intro will walk you through creating a new Refinery project and deploying it to production.

For our example app we will make a simple "Hello World" script which will execute on a five minute interval.

## Creating a New Project

<video style="width: 100%" controls autoplay muted loop>
	<source src="/quickstart/images/create-new-project.webm" type="video/webm" />
	<source src="/quickstart/images/create-new-project.mp4" type="video/mp4" />
</video>

Create a new project by navigating to the [All Projects](https://app.refinery.io/projects). Enter the project name into the `Project Name` textbox and click `Create Project`.

## Adding a Block

<video style="width: 100%" controls autoplay muted loop>
	<source src="/quickstart/images/add-code-block.webm" type="video/webm" />
	<source src="/quickstart/images/add-code-block.mp4" type="video/mp4" />
</video>

Now we'll add our Code Block to project. We'll start by click on the `Add Block` button on the left side of the project. Change the `Block Name` to be `Example Block` and click on the `Save Block` button to save the change.

Now that you have a new Code Block, select one of the following languages under the `Block Runtime` block editor section which you are the most familiar with:

* Node 8.10
* Python 2.7
* PHP 7.3
* Go 1.12

<video style="width: 100%" controls autoplay muted loop>
	<source src="/quickstart/images/writing-hello-world-python.webm" type="video/webm" />
	<source src="/quickstart/images/writing-hello-world-python.mp4" type="video/mp4" />
</video>

Once you've selected a language you can now start writing some code. In our example we'll choose Python 2.7 and we'll edit the block code to be the following:

```python
def main(lambda_input, context):
    print("Hello world!")
    return False
```

This is a simple script which will just print `Hello world!` upon executing. Once you've written your `Hello World` script you can save the block by clicking the blue `Save Block` button.

## Adding a Timer Block

Now, let's make our script run every five minutes. Click on the `Add Block` button on the right panel to add another block. This time click on the `Timer Block` to add a block which will automatically trigger all blocks connected to it on a set interval.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/adding-timer-block.webm" type="video/webm" />
	<source src="/quickstart/images/adding-timer-block.mp4" type="video/mp4" />
</video>

Just like with the `Code Block`, with the `Timer Block` we can rename the block and save the changes by clicking on the `Save Block` button.

By default the `Timer Block` is set to trigger every 2 minutes. Change the `Schedule Expression` to be `rate(5 minutes)` instead of `rate(2 minutes)` to achieve this.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/change-timer-block-interval.webm" type="video/webm" />
	<source src="/quickstart/images/change-timer-block-interval.mp4" type="video/mp4" />
</video>

## Connecting Blocks

We now have all the blocks for our service but we still need to link them together. Click on the `Add Transition` button in the left side of the project to view the possible transitions. Next click on the `Then Transition` option. You will now see that the `Example Block` is flashing. This indicates that you can transition to it from the selected `Timer Block` via the transition that you selected. Click on the flashing `Example Block` to create a transition between the blocks.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/adding-transition-example.webm" type="video/webm" />
	<source src="/quickstart/images/adding-transition-example.mp4" type="video/mp4" />
</video>

Great! You've now created your first Refinery service. Click on the `Save Project` button on the left side of the screen to save your progress.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/saving-project.webm" type="video/webm" />
	<source src="/quickstart/images/saving-project.mp4" type="video/mp4" />
</video>

## Deploying a Project

Now that we have our service created, let's deploy it! Click on the `Deploy Project` button on the left side of the page. A dialogue box will confirm that you want to deploy the project, click the `Confirm Deploy` button to do so. After a few seconds your service will be deployed and you'll be shown your newly-deployed project.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/deploy-project.webm" type="video/webm" />
	<source src="/quickstart/images/deploy-project.mp4" type="video/mp4" />
</video>

Congratulations, you've deployed your first service with Refinery! Your script will now be executed every five minutes until you destroy your deployment. Since Refinery deploys to serverless you'll never have to manage the servers that run your script and you'll only be billed for the time the script is actually being run.

## Destroying a Project

Since you probably don't want this simple script executing forever, let's tear it down. Click the `Destroy Deploy` button to delete your newly-deployed service. Confirm your intention by clicking on the `Destroy Deployment` button in the confirmation prompt.

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/quickstart/images/destroy-project.webm" type="video/webm" />
	<source src="/quickstart/images/destroy-project.mp4" type="video/mp4" />
</video>

## Moving Forward

Now that you've build something really simple with Refinery, why not build something a bit more complex? Head over to some of these articles to learn about more Refinery features:

* [The Refinery Blocks](/blocks/)
* [The Refinery Transitions](/transitions/)