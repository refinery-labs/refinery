# Refinery Pipeline Memory

## Summary

A Refinery Pipeline consists of many Lambdas chained together in a larger state diagram. Since each Lambda's run-time memory is gone after its execution has completed, long-term memory is needed. Refinery provides a few different types of "longer term" storage memory.

## Types of Memory & Storage

### Config Memory

Config memory is read only and is for purely configuration data which needs to be read at run-time. This memory can only be edited inside of the Refinery IDE or via the Refinery API.

Some examples of the type of things to use this memory for include the following:

* AWS Access Keys
* Third Party Access Keys
* Hostnames of Services Used in Pipelines

### Runtime Memory

Runtime Memory can be thought of as your pipeline's RAM. This memory is only accessible during the runtime of your pipeline's execution. After the pipeline has finished this memory will be automatically deleted. This memory is useful for keeping state between Lambda executions and encourages building better stateless Lambdas.

Without Runtime Memory all program state would have to be passed in the return data of each Lambda to the next Lambda. This would mean it would be very unpleasant to build re-usable Lambdas as components. With Runtime Memory you can stash data into this memory and pass specific data to a reusable Lambda component you've previously built. After the reusable component finishes you can then pull the state back out of Runtime Memory and continue on with your work.

The following diagram illustrates Runtime Memory usage:

```
 ______________________
|                      |
|      SQS Queue       | 
|______________________|
         ||
         || Return data of job data
         ||
         \/
 ______________________
|                      |
|    Stash job ID      |
|  and kick things off | ---Store "job_id" in Runtime Memory---> 
|______________________|
         ||
         || Return URL string
         ||
         \/
 ______________________
|                      |
|     Get URL HTML     | 
|______________________|
         ||
         || Returns URL HTML string
         ||
         \/
 ______________________
|                      |
|  Get Links from HTML | 
|______________________|
         ||
         || Return list of links and their text + link URL
         ||
         \/
 ______________________
|                      |
|    Store Results     |
|                      | <---Get "job_id" from Runtime Memory---
|______________________|
         ||
         || Return data to store in DB [ { "job_id": "341", "links": [...] } ]
         ||
         \/
 ______________________
|                      |
|       Cloud DB       | 
|______________________|
```

In the above diagram the "Get URL HTML", and "Get Links from HTML" Lambdas are examples of "component" Lambdas. They have a structure input and output format and **don't** make use of Runtime Memory. Since they're purely functional they can be saved and added into other projects with extreme ease. Before using these "component" Lambdas the "Stash job ID and kick things off" Lambda stores the job ID in Runtime Memory. This is later retrieved after the component Lambdas have completed to re-correlate the data with the job ID before storing the results in the cloud database.

Note that the total Runtime Memory is of a static size and can be configured in the Refinery IDE. This is ultimately backed by a cluster of Redis instances which allow for high throughput reading and writing.