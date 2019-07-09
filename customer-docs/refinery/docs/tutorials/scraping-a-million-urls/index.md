# Scraping a Million URLs in a Lunch Break

Refinery makes it easy to do a large amount of distributed computation without having to learn any new APIs or managed infrastructure. Our editor allows developers to do highly-scaled operations without having to know anything about the underlying infrastructure making it happen. In this tutorial we'll show how to create a project to scrape a million URLs with Refinery in as little as the time you'd usually use take your lunch break.

One common architecture that is created when a large amount of work needs to be done is a [job queue](https://en.wikipedia.org/wiki/Job_queue) with distributed workers. In this pattern you have a queue which is used to dispatch jobs to workers which do some operation with the job data. This pattern is useful because you can horizontally scale up the number of workers to do more things in parallel.

However, while the design pattern is fairly simple to describe it is much more challenging to actually implement. To put it bluntly "easier said than done". With convention cloud services you would have to learn and configure multiple cloud services to do queue management, job dispatching to workers, auto-scaling compute instances, key management, and more. This normally would take even an engineer who is experienced with AWS a few days or even weeks to create. With Refinery however, you just have to link together three blocks in our editor and we'll do the rest.

!!! note
	This tutorial assumes you have some familiarity with the Refinery editor. If you've never used Refinery before you should read through the [Getting Started](/getting-started/) documentation.

## Creating a Distributed Job Queue & Worker System in Refinery

The following is an example Refinery diagram of this system, consisting of just three blocks:

<center>
	<img src="/tutorials/scraping-a-million-urls/media/worker-queue-diagram.png" />
</center>

### Put Some Items in the Queue (the URLs to Scrape)

The first `Code Block` "Return URL Array" pulls a list of URLs and returns it as an array. In this case we'll use the Alexa top 1 million URLs to do this.

The following Python code will do this for you, note that there are two tabs below: one for just using the first 100 URLs in the list and one for using the full list. This is so that you can do a small test before going all-out with the scraping:

``` python tab="Return 100 URLs (Recommended for Testing)"
import requests

def main(block_input, backpack):
    response = requests.get(
        "https://gist.githubusercontent.com/mandatoryprogrammer/1de2d26f0125ee4d62943cfdc7709c16/raw/b7ccca6115e5e86a80bf3f87a15164810228de94/top-1m.txt"
    )
    
    # Turn response into domain list
    domain_list = response.text.split(
        "\n"
    )
    
    # Turn domains into URLs
    url_list = []
    for domain in domain_list:
        url_list.append(
            "http://" + domain
        )
    
    # For testing we'll just use the first 100 URLs
    url_list = url_list[:100]
    
    # Return URLs for the queue
    return url_list
```

``` python tab="Return 1 Million URLs"
import requests

def main(block_input, backpack):
    response = requests.get(
        "https://gist.githubusercontent.com/mandatoryprogrammer/1de2d26f0125ee4d62943cfdc7709c16/raw/b7ccca6115e5e86a80bf3f87a15164810228de94/top-1m.txt"
    )
    
    # Turn response into domain list
    domain_list = response.text.split(
        "\n"
    )
    
    # Turn domains into URLs
    url_list = []
    for domain in domain_list:
        url_list.append(
            "http://" + domain
        )
    
    # Return URLs for the queue
    return url_list
```

!!! note
	You'll also need to add the `requests` Python library to your `Code Block`. You can do this by clicking `Modify Libraries` under the `Block Imported Libraries` section of the `Edit Block` pane. You then just type in `requests` for the Library Name and click `Add Library`.

When you connect a `Code Block` to a `Queue Block` all of the items in the array that you return will automatically be added onto the queue. For example, if you return an array of 100 values then 100 items will be placed on the queue. This works the same whether you're returning 100 items in your array or if you're returning a million items in your array.

The magic of the `Queue Block` in Refinery is that it will automatically kick off and scale the `Code Block` which is connected downstream to it (in this example, the "Scrape URL" `Code Block`). The number of concurrent executions of the `Code Block` will continually increase until you've either maxed-out your default concurrency amount (1,000 concurrent executions to start with by default in Refinery accounts), or you've emptied out your queue. This means that you don't have to think about scaling up the number of workers - it is automatically done for you.

### The Scraper Code Block ("Scrape URL")

We now need to create a block to do the actual scraping of the URL. The following Python demonstrates this:

```python
import sys
import codecs
import requests

# Purely to make Python 2.7 handle Unicode gracefully :)
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

def main(block_input, backpack):
    url = block_input[0]
    
    # Pull URL
    try:
        response = requests.get(
            url,
            timeout=5 # 5 second timeout
        )
        response_data = response.text
    except:
        print( "An error occurred while grabbing our URL!" )
        response_data = ""
    
    
    # Do something with response
    print( response_data )
    
    return response_data

```

!!! note
	You'll also need to add the `requests` Python library to your `Code Block`. You can do this by clicking `Modify Libraries` under the `Block Imported Libraries` section of the `Edit Block` pane. You then just type in `requests` for the Library Name and click `Add Library`.

Note that while this is a simple blocking request, it is still sufficient to scrape a million URLs. This is because it will be executed at extremely-high concurrency, and so the fact that it is technically blocking is not a deal-breaker. Since all the blocks in Refinery are extremely moduler we can always improve our system later by replacing this block with a version that can handle a large batch amount (e.g. 10 at a time).

### Adding a `Queue Block`

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/tutorials/scraping-a-million-urls/media/add-queue-block.webm" type="video/webm" />
	<source src="/tutorials/scraping-a-million-urls/media/add-queue-block.mp4" type="video/mp4" />
</video>

Adding a `Queue Block` can be accomplished by clicking on the `Add Block` button on the left-side of the page and clicking `Queue Block` from the list of blocks to add. You can then rename the block to something more familiar such as `URL Queue Block`. This is all the configuration you have to do for this block unless you want to change the number of messages sent in a batch (up to 10 at a time).

### Tying It All Together

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/tutorials/scraping-a-million-urls/media/linking-blocks-together.webm" type="video/webm" />
	<source src="/tutorials/scraping-a-million-urls/media/linking-blocks-together.mp4" type="video/mp4" />
</video>

Now we just have to connect our blocks together. Select the `Return URL Array` block and click on the `Add Transition` button on the left-side of the screen. Choose the `Then Transition` option and click on the flashing `URL Queue Block` to add the transition from the `Return URL Array` block to the `URL Queue Block`. Repeat this process to connect the `URL Queue Block` to the `Scrape URL` block.

### Deploy Your New Project

<video style="width: 100%" playsinline controls autoplay muted loop>
	<source src="/tutorials/scraping-a-million-urls/media/deploy-project.webm" type="video/webm" />
	<source src="/tutorials/scraping-a-million-urls/media/deploy-project.mp4" type="video/mp4" />
</video>

Now that you've finished building your distributed worker queue system, you can deploy it into production by clicking the `Deploy Project` button on the left-side of the page. Confirm the action by clicking the `Confirm Deploy` button on the pop up panel. After a short wait your code will be deployed into production and is now ready to run!

### Running Your Production Pipeline

You can now kick off your production project by clicking the `Return URL Array` block and clicking the `Code Runner` button. Click the `Execute with Data` button to kick off your execution pipeline. Once you've started it you can monitor the status of it by clicking on the `Block Executions` button. To get detailed information on the executions as they occur you can click on the execution pipeline logs from the list of executions.

### That's All Folks

You've successfully created a project which can handle a million jobs and automatically scale to meet demand. Pat yourself on the back!

Why not try some of these other fun projects?:

* [Effortless Serverless Map Reduce](/tutorials/scraping-a-million-urls/)
* [Creating a Highly Scalable API Endpoint](/tutorials/api-endpoints/)