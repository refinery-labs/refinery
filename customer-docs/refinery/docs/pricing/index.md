# Pricing Details

## What is a Queue "Action"?

Since there are a few different operations that can be done on a queue, we use "actions" to explain how much each queue operation costs.

The following are examples of operations equivalent to one action:

* Adding up to 10 messages to the queue is one action. If you add 100 messages to the queue this is 10 actions. We automatically make adding to the queue batched so that you incur the least cost for putting a lot of messages in the queue.
* Taking off one batch of messages (up to 10 at a time) is one action. If you take 20 messages off the queue in batches of 5, that's 4 actions.
* 64KB of data is 1 action. So if you add 10 messages and it's less than 64K in size that's one action. If you add 10 messages and it's 80KB in size, that's two actions. The max message size for a queue is currently 256KB.