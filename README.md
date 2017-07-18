## What it does

You can ask SBot about the price of spot instances in Slack. 

You can simply ask: "What is the current price of c4.large instances?"

If you are not sure about the available AWS instance types you can ask: "Which instance types have at least 30 CPU and 128GB RAM?"

And finally, you can ask for the cheapest instance types in your region: "What are the cheapest instance types with at least 4 CPU and 10 GB of memory?"

## More information

This project has been submitted to the AWS Chatbot Challenge 2017. [Visit the project page for more information.](https://devpost.com/software/sbot)

This project uses Amazon Lex and AWS Lambda.

## What's next for SBot

 * Display prices for other products than  `Linux/UNIX (Amazon VPC)`. 
 * Have a dynamic list of instance types that reflects the current AWS instance types
 * If the user enters for example "Dublin" or "Ireland", then the bot would understand that it's for the eu-west-1 region (no more need to enter the Amazon region code)
 * Possibility to ask new questions like the region where a specific instance type is the cheapest or provide price history for a specific instance type. 

SBot icon by [Freepik](http://www.freepik.com)