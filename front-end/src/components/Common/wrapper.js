// THIS CODE IS GARBAGE DESIGNER TRASH

/**
 * This library was created to emulate some jQuery features
 * used in this template only with Javascript and DOM
 * manipulation functions (IE10+).
 * All methods were designed for an adequate and specific use
 * and don't perform a deep validation on the arguments provided.
 *
 * IMPORTANT:
 * ==========
 * It's suggested NOT to use this library extensively unless you
 * understand what each method does. Instead, use only JS or
 * you might even need jQuery.
 */

export default (function() {
  // HELPERS
  function arrayFrom(obj) {
    return 'length' in obj && obj !== window ? [].slice.call(obj) : [obj];
  }

  function filter(ctx, fn) {
    return [].filter.call(ctx, fn);
  }

  function map(ctx, fn) {
    return [].map.call(ctx, fn);
  }

  function matches(item, selector) {
    return (
      Element.prototype.matches || Element.prototype.msMatchesSelector
    ).call(item, selector);
  }

  // Events handler with simple scoped events support
  const EventHandler = function() {
    this.events = {};
  };
  EventHandler.prototype = {
    // event accepts: 'click' or 'click.scope'
    bind: function(event, listener, target) {
      const type = event.split('.')[0];
      target.addEventListener(type, listener, false);
      this.events[event] = {
        type: type,
        listener: listener
      };
    },
    unbind: function(event, target) {
      if (event in this.events) {
        target.removeEventListener(
          this.events[event].type,
          this.events[event].listener,
          false
        );
        delete this.events[event];
      }
    }
  };

  // Object Definition
  const Wrap = function(selector) {
    this.selector = selector;
    return this._setup([]);
  };

  // CONSTRUCTOR
  Wrap.Constructor = function(param, attrs) {
    const el = new Wrap(param);
    return el.init(attrs);
  };

  // Core methods
  Wrap.prototype = {
    constructor: Wrap,
    /**
     * Initialize the object depending on param type
     * [attrs] only to handle $(htmlString, {attributes})
     */
    init: function(attrs) {
      // empty object
      if (!this.selector) return this;
      // selector === string
      if (typeof this.selector === 'string') {
        // if looks like markup, try to create an element
        if (this.selector[0] === '<') {
          const elem = this._setup([this._create(this.selector)]);
          return attrs ? elem.attr(attrs) : elem;
        } else
          return this._setup(
            arrayFrom(document.querySelectorAll(this.selector))
          );
      }
      // selector === DOMElement
      if (this.selector.nodeType) return this._setup([this.selector]);
      // shorthand for DOMReady
      else if (typeof this.selector === 'function')
        return this._setup([document]).ready(this.selector);
      // Array like objects (e.g. NodeList/HTMLCollection)
      return this._setup(arrayFrom(this.selector));
    },
    /**
     * Creates a DOM element from a string
     * Strictly supports the form: '<tag>' or '<tag/>'
     */
    _create: function(str) {
      const nodeName = str
        .substr(str.indexOf('<') + 1, str.indexOf('>') - 1)
        .replace('/', '');
      return document.createElement(nodeName);
    },
    /** setup properties and array to element set */
    _setup: function(elements) {
      let i = 0;
      for (; i < elements.length; i++) delete this[i]; // clean up old set
      this.elements = elements;
      this.length = elements.length;
      for (let i = 0; i < elements.length; i++) this[i] = elements[i]; // new set
      return this;
    },
    _first: function(cb, ret) {
      const f = this.elements[0];
      return f ? (cb ? cb.call(this, f) : f) : ret;
    },
    /** Common function for class manipulation  */
    _classes: function(method, classname) {
      const cls = classname.split(' ');
      if (cls.length > 1) {
        cls.forEach(this._classes.bind(this, method));
      } else {
        if (method === 'contains') {
          const elem = this._first();
          return elem ? elem.classList.contains(classname) : false;
        }
        return classname === ''
          ? this
          : this.each(function(i, item) {
              item.classList[method](classname);
            });
      }
    },
    /**
     * Multi purpose function to set or get a (key, value)
     * If no value, works as a getter for the given key
     * key can be an object in the form {key: value, ...}
     */
    _access: function(key, value, fn) {
      if (typeof key === 'object') {
        for (let k in key) {
          this._access(k, key[k], fn);
        }
      } else if (value === undefined) {
        return this._first(function(elem) {
          return fn(elem, key);
        });
      }
      return this.each(function(i, item) {
        fn(item, key, value);
      });
    },
    each: function(fn, arr) {
      arr = arr ? arr : this.elements;
      for (let i = 0; i < arr.length; i++) {
        if (fn.call(arr[i], i, arr[i]) === false) break;
      }
      return this;
    }
  };

  /** Allows to extend with new methods */
  Wrap.extend = function(methods) {
    Object.keys(methods).forEach(function(m) {
      Wrap.prototype[m] = methods[m];
    });
  };

  // DOM READY
  Wrap.extend({
    ready: function(fn) {
      if (document.attachEvent) {
        if (document.readyState === 'complete') {
          fn();
        } else {
          document.addEventListener('DOMContentLoaded', fn);
        }
      } else {
        if (document.readyState !== 'loading') {
          fn();
        } else {
          document.addEventListener('DOMContentLoaded', fn);
        }
      }
      return this;
    }
  });
  // ACCESS
  Wrap.extend({
    /** Get or set a css value */
    css: function(key, value) {
      const getStyle = function(e, k) {
        return e.style[k] || getComputedStyle(e)[k];
      };
      return this._access(key, value, function(item, k, val) {
        const unit = typeof val === 'number' ? 'px' : '';
        return val === undefined
          ? getStyle(item, k)
          : (item.style[k] = val + unit);
      });
    },
    /** Get an attribute or set it */
    attr: function(key, value) {
      return this._access(key, value, function(item, k, val) {
        return val === undefined
          ? item.getAttribute(k)
          : item.setAttribute(k, val);
      });
    },
    /** Get a property or set it */
    prop: function(key, value) {
      return this._access(key, value, function(item, k, val) {
        return val === undefined ? item[k] : (item[k] = val);
      });
    },
    position: function() {
      return this._first(function(elem) {
        return { left: elem.offsetLeft, top: elem.offsetTop };
      });
    },
    scrollTop: function(value) {
      return this._access('scrollTop', value || 0, function(item, k, val) {
        return val === undefined ? item[k] : (item[k] = val);
      });
    },
    outerHeight: function(includeMargin) {
      return this._first(function(elem) {
        const style = getComputedStyle(elem);
        const margins = includeMargin
          ? parseInt(style.marginTop, 10) + parseInt(style.marginBottom, 10)
          : 0;
        return elem.offsetHeight + margins;
      });
    },
    /**
     * Find the position of the first element in the set
     * relative to its sibling elements.
     */
    index: function() {
      return this._first(function(el) {
        return arrayFrom(el.parentNode.children).indexOf(el);
      }, -1);
    }
  });
  // LOOKUP
  Wrap.extend({
    children: function(selector) {
      let childs = [];
      this.each(function(i, item) {
        childs = childs.concat(
          map(item.children, function(item) {
            return item;
          })
        );
      });
      return Wrap.Constructor(childs).filter(selector);
    },
    siblings: function() {
      let sibs = [];
      this.each(function(i, item) {
        sibs = sibs.concat(
          filter(item.parentNode.children, function(child) {
            return child !== item;
          })
        );
      });
      return Wrap.Constructor(sibs);
    },
    /** Return the parent of each element in the current set */
    parent: function() {
      const par = map(this.elements, function(item) {
        return item.parentNode;
      });
      return Wrap.Constructor(par);
    },
    /** Return ALL parents of each element in the current set */
    parents: function(selector) {
      const par = [];
      this.each(function(i, item) {
        for (let p = item.parentElement; p; p = p.parentElement) par.push(p);
      });
      return Wrap.Constructor(par).filter(selector);
    },
    /**
     * Get the descendants of each element in the set, filtered by a selector
     * Selector can't start with ">" (:scope not supported on IE).
     */
    find: function(selector) {
      let found = [];
      this.each(function(i, item) {
        found = found.concat(
          map(item.querySelectorAll(/*':scope ' + */ selector), function(
            fitem
          ) {
            return fitem;
          })
        );
      });
      return Wrap.Constructor(found);
    },
    /** filter the actual set based on given selector */
    filter: function(selector) {
      if (!selector) return this;
      const res = filter(this.elements, function(item) {
        return matches(item, selector);
      });
      return Wrap.Constructor(res);
    },
    /** Works only with a string selector */
    is: function(selector) {
      let found = false;
      this.each(function(i, item) {
        return !(found = matches(item, selector));
      });
      return found;
    }
  });
  // ELEMENTS
  Wrap.extend({
    /**
     * append current set to given node
     * expects a dom node or set
     * if element is a set, prepends only the first
     */
    appendTo: function(elem) {
      elem = elem.nodeType ? elem : elem._first();
      return this.each(function(i, item) {
        elem.appendChild(item);
      });
    },
    /**
     * Append a domNode to each element in the set
     * if element is a set, append only the first
     */
    append: function(elem) {
      elem = elem.nodeType ? elem : elem._first();
      return this.each(function(i, item) {
        item.appendChild(elem);
      });
    },
    /**
     * Insert the current set of elements after the element
     * that matches the given selector in param
     */
    insertAfter: function(selector) {
      const target = document.querySelector(selector);
      return this.each(function(i, item) {
        target.parentNode.insertBefore(item, target.nextSibling);
      });
    },
    /**
     * Clones all element in the set
     * returns a new set with the cloned elements
     */
    clone: function() {
      const clones = map(this.elements, function(item) {
        return item.cloneNode(true);
      });
      return Wrap.Constructor(clones);
    },
    /** Remove all node in the set from DOM. */
    remove: function() {
      this.each(function(i, item) {
        delete item.events;
        delete item.data;
        if (item.parentNode) item.parentNode.removeChild(item);
      });
      this._setup([]);
    }
  });
  // DATASETS
  Wrap.extend({
    /**
     * Expected key in camelCase format
     * if value provided save data into element set
     * if not, return data for the first element
     */
    data: function(key, value) {
      const hasJSON = /^(?:{[\w\W]*}|\[[\w\W]*])$/,
        dataAttr = 'data-' + key.replace(/[A-Z]/g, '-$&').toLowerCase();
      if (value === undefined) {
        return this._first(function(el) {
          if (el.data && el.data[key]) return el.data[key];
          else {
            const data = el.getAttribute(dataAttr);
            if (data === 'true') return true;
            if (data === 'false') return false;
            if (data === +data + '') return +data;
            if (hasJSON.test(data)) return JSON.parse(data);
            return data;
          }
        });
      } else {
        return this.each(function(i, item) {
          item.data = item.data || {};
          item.data[key] = value;
        });
      }
    }
  });
  // EVENTS
  Wrap.extend({
    trigger: function(type) {
      type = type.split('.')[0]; // ignore namespace
      const event = document.createEvent('HTMLEvents');
      event.initEvent(type, true, false);
      return this.each(function(i, item) {
        item.dispatchEvent(event);
      });
    },
    blur: function() {
      return this.trigger('blur');
    },
    focus: function() {
      return this.trigger('focus');
    },
    on: function(event, callback) {
      return this.each(function(i, item) {
        if (!item.events) item.events = new EventHandler();
        event.split(' ').forEach(function(ev) {
          item.events.bind(ev, callback, item);
        });
      });
    },
    off: function(event) {
      return this.each(function(i, item) {
        if (item.events) {
          item.events.unbind(event, item);
          delete item.events;
        }
      });
    }
  });
  // CLASSES
  Wrap.extend({
    toggleClass: function(classname) {
      return this._classes('toggle', classname);
    },
    addClass: function(classname) {
      return this._classes('add', classname);
    },
    removeClass: function(classname) {
      return this._classes('remove', classname);
    },
    hasClass: function(classname) {
      return this._classes('contains', classname);
    }
  });

  return Wrap.Constructor;
})();
