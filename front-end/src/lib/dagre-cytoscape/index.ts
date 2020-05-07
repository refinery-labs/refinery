import { DagreLayout } from './layout';

// registers the extension on a cytoscape lib ref
export function registerCustomDagre(cytoscape: (extensionName: string, foo: string, bar: any) => cytoscape.Core) {
  // can't register if cytoscape unspecified
  if (!cytoscape) {
    throw new Error('Unable to register dagre due to missing Cytoscape instance');
  }

  /**
   * Copied from here:
   * https://stackoverflow.com/questions/4152931/javascript-inheritance-call-super-constructor-or-use-prototype-chain
   * @param base
   * @param sub
   */
  function extend(base: any, sub: any) {
    // Avoid instantiating the base class just to setup inheritance
    // Also, do a recursive merge of two prototypes, so we don't overwrite
    // the existing prototype, but still maintain the inheritance chain
    // Thanks to @ccnokes
    const origProto = sub.prototype;
    sub.prototype = Object.create(base.prototype);
    for (let key in origProto) {
      // noinspection JSUnfilteredForInLoop
      sub.prototype[key] = origProto[key];
    }
    // The constructor property was set wrong, let's fix it
    Object.defineProperty(sub.prototype, 'constructor', {
      enumerable: false,
      value: sub
    });
  }

  /**
   * This is one of the nastiest hacks that I've ever had to do. Essentially, Cytoscape doesn't use the 'new' keyword
   * and we wrote DagreLayout as an ES6+ class... And so this breaks (when not polyfilled).
   * Instead of polyfill _the entire app_ we can just shim this here.
   * @param options
   * @constructor
   */
  function CytoscapeLegacyShim(options: any) {
    const dagreInstance = new DagreLayout(options);

    // Copy over internal variables from the instance.
    // @ts-ignore
    Object.assign(this, dagreInstance);
  }

  // FooTest.prototype = DagreLayout;
  extend(DagreLayout, CytoscapeLegacyShim);

  cytoscape('layout', 'dagre', CytoscapeLegacyShim); // register with cytoscape.js
}
