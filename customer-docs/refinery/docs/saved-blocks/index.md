# Using Saved Blocks

## What are Saved Blocks?

Refinery has the first universal component repository which allows users to publish and re-used [`Code Blocks`](/blocks/#code-block) in any programming language. A PHP developer can publish a PHP `Code Block` on Refinery and a Node developer using Refinery can immediately add it to their own project and start using it. As our community grows, more and more saved `Code Blocks` will be published and developers will have to spend less and less time writing the nitty-gritty functionality for their services.

## Saved Block Example: Create an "Add Email to Mailing List" API Endpoint

To demonstrate the usefulness of saved blocks we'll go over how to create an API endpoint which:

* Takes an `email` parameter
* Validates that the email address is valid and can be used (using Mailgun).
* If valid, adds the email address to our Mailgun mailing list.

Since there's already a published `Code Block` in Refinery for doing this, this is an easy feature to add.

### Creating the API Endpoint Block

<video style="width: 100%" controls autoplay muted loop>
	<source src="/saved-blocks/media/add-api-endpoint-blocks.webm" type="video/webm" />
	<source src="/saved-blocks/media/add-api-endpoint-blocks.mp4" type="video/mp4" />
</video>

First we'll add an `API Endpoint Block` to our project, click the `Add Block` button and select `API Endpoint Block`. This will add an `API Endpoint Block` and an `API Response Block` to the canvas. For serving up web requests you must connect an `API Endpoint Block` to one or more `Code Blocks` which are connected to an `API Response Block`. You can think of the web request as triggering a chain of events which eventually ends up flowing to the `API Response Block` (which of course writes the ressponse).

You can modify the `HTTP Path` to be something more friendly than the randomly-generated default value. In the above example we edit the path to be `/v1/mailinglist/add`.

### Adding the "Mailgun Validate & Add Email to Email List" Saved Block

<video style="width: 100%" controls autoplay muted loop>
	<source src="/saved-blocks/media/add-saved-mailgun-email-list.webm" type="video/webm" />
	<source src="/saved-blocks/media/add-saved-mailgun-email-list.mp4" type="video/mp4" />
</video>

Refinery allows any of its users to publish the `Code Blocks` they've written to the Community Block Repository. Once they've been publically published any Refinery user can than add them to their own project and immediately start using them. The best part is that they are not limited by any specific programming language, you can publish a PHP `Code Block` and it can be used by programmers who only know Go, Node, or any other programming language.

We'll demonstrate the time you can save by using an existing saved block from the Community Block Repository. In your project, click `Add Block` and select `Saved Block/Community Repository Block`. Then you can search for `Mailgun Validate & Add Email to Email List` block and select it.

Once you've selected the block you can see the Markdown description of the block as well as some example input data the block expects. Before you can add a published block you may need to configure the `Block Settings`. `Block Settings` are fields which need to be filled out with configuration values for the block to run.

In this example, the block requires two `Block Settings` to be configured before we can add it to our project:

* `mailgun_mailing_list`: This is the email address of the Mailgun mailing list you wish to add validated-emails to.
* `mailgun_api_key`: The Mailgun API key for your account, used to authenticate to the Mailgun API.

You can fill out these values using the URLs provided in the Saved Block description. Once you've done so you can add the block to your project by clicking the `Add Block` button.

### Tying It All Together

<video style="width: 100%" controls autoplay muted loop>
	<source src="/saved-blocks/media/connect-saved-mailgun-email-list-block-to-api-endpoint.webm" type="video/webm" />
	<source src="/saved-blocks/media/connect-saved-mailgun-email-list-block-to-api-endpoint.mp4" type="video/mp4" />
</video>

Now we just need to tie all of this together. Click the `API Endpoint Block` and click `Add Transition`. Select `Then Transition` and click the `Code Block`. Do the same thing again to connect the `Code Block` to the `API Endpoint Response Block`.

We now have a fully-configured project that we can deploy!

### Deploying the Project

<video style="width: 100%" controls autoplay muted loop>
	<source src="/saved-blocks/media/deploy-email-list-project.webm" type="video/webm" />
	<source src="/saved-blocks/media/deploy-email-list-project.mp4" type="video/mp4" />
</video>

Click the `Deploy Project` button and confirm by clicking the `Confirm Deploy` button. You've now deployed your project to the Internet and can start using it!

### Trying Out Your New Endpoint

<video style="width: 100%" controls autoplay muted loop>
	<source src="/saved-blocks/media/demonstration-of-deployed-api-endpoint.webm" type="video/webm" />
	<source src="/saved-blocks/media/demonstration-of-deployed-api-endpoint.mp4" type="video/mp4" />
</video>

Click on the `API Endpoint Block` in the deployed diagram, the full URL of your deployed endpoint will be shown. Click on the URL to open it in your web browser, you should see a message stating that you need to provide an `email` parameter for the endpoint.

Provide an `email` parameter of both a valid and invalid email to test it out. The above example shows adding `support@refinery.io` via the `email` parameter which validates successfully and is added to the Mailgun mailing list.

### Many More Saved Blocks

This is just one of the published Code Blocks available on the platform. Do you want to scrape a list of URLs from a webpage? Send an SMS with Twilio? There's published blocks for that as well!