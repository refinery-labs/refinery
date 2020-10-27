const main = require('./refinery_main').main;

exports.handler = async (event) => {
  const backpack = event.hasOwnProperty('backpack') ? event['backpack'] : {};
  const result = await main(
    event.hasOwnProperty('block_input') ? event['block_input'] : {},
    backpack
  );
  const response = {
    result: result,
    backpack: backpack
  };
  return JSON.stringify(response)
};
