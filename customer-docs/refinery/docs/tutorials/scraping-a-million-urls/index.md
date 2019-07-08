# Scraping a Million URLs in a Lunch Break

Refinery makes it easy to do a large amount of distributed computation without having to learn any new APIs or managed infrastructure. Our editor allows developers to do highly-scaled operations without having to know anything about the underlying infrastructure making it happen. In this tutorial we'll show how to create a project to scrape a million URLs with Refinery in as little as the time you'd usually use take your lunch break.

One common architecture that is created when a large amount of work needs to be done is a [job queue](https://en.wikipedia.org/wiki/Job_queue) with distributed workers. In this pattern you have a queue which is used to dispatch jobs to workers which do some operation with the job data. This pattern is useful because you can horizontally scale up the number of workers to do more things in parallel.

However, while the design pattern is fairly simple to describe it is much more challenging to actually implement. To put it bluntly "easier said than done". With convention cloud services you would have to learn and configure multiple cloud services to do queue management, job dispatching to workers, auto-scaling compute instances, key management, and more. With Refinery however, you just have to link together three blocks in our editor and we'll do the rest.

## The Queue Block

One of the block types in the Refinery editor is the [`Queue Block`](/blocks/#queue-block).