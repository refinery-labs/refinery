const main = require("./refinery_main").main;

exports.handler = async (event) => {
   const result = await main(
        event.hasOwnProperty("block_input") ? event['block_input'] : {},
        event.hasOwnProperty("backpack") ? event['backpack'] : {}
    );
   const response = {
     result: result,
     backpack: backpack
   };
   return JSON.stringify(response)
};
