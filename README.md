# Microservices Demo

## Purpose
This is a quick and dirty demo of some 5 microservices that do very simple things to a set of numbers, passing messages between eachother via Kafka topics.

It was built in order to show what's possible, and provide a skeleton framework that could be used/extended as needed.

## Usage

Running the demo is as simple as cloning the repo, ensuring you're got Docker and docker-compose, and then running `docker-compose up -d --build`.

That will build all the stage containers, and run everything (Zookeeper, Kafka, Postgres, UIs, and stages).

The Kafka UI is available on port 18080 and the Postgres UI is on port 18081.

### Posting messages to start flow

Load up the Kafka UI, to to **Topics** on the left side, then click on **start** in the list of topics presented.

Click on **Produce Message** in the top right corner, and in the *Value* section of the blade, enter a list of numbers, like this:

```json
{
  "numbers": [
    76452,
    61211234,
    8243724
  ]
}
```
There can be as many numbers as you want in the `numbers` array.

This will kick-off the pipeline. If you click back to the list of Topics, you'll see that eventually, all the stages will show the same number of messages as `start`, with the final output being in `finish`. 

You can see the state of the message object at the end of each stage by going into their respective topics, and looking at the messages.

Also, the output of any given stage is stored in the Postgres DB. This would allow for re-constructing a message for re-submission to any stage along the way.

## Notes

This demo isn't complete any any means. No input validation is performed, and only the most basic of logging is being done, but it does still serve as it's purpose.

There's almost certainly lots of optimization that could be done in order to modularize some of the base infrastructure of the pipeline ((de)-serializing of data, consuming from/publishing to Kafka, saving to Postgres, etc..), but that's beyond the scope of this demo.