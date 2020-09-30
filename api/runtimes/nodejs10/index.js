const main = require("./refinery_main").main

exports.handler = async (event) => {
   return await main(
        event.hasOwnProperty("blockInput") ? event['blockInput'] : {},
        event.hasOwnProperty("backpack") ? event['backpack'] : {}
    );
}