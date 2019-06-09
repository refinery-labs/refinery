export const STRIPE_LIB_URL = 'https://js.stripe.com/v3/';

export function loadScript(src: string) {

  const scriptTagElement = document.querySelector(`script[src="${src}"]`);

  // Check if the tag was already mounted on the page.
  if (scriptTagElement !== null) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    // Create script element and set attributes
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = src;

    // Append the script to the DOM
    const el = document.getElementsByTagName('script')[0];

    if (!el || !el.parentNode) {
      console.error('Could not load script tag', src);
      return;
    }

    el.parentNode.insertBefore(script, el);

    // Resolve the promise once the script is loaded
    script.addEventListener('load', () => {
      resolve(script);
    });

    // Catch any errors while loading the script
    script.addEventListener('error', () => {
      reject(new Error(`Script failed to load (${src}).`))
    });
  });
}

/**
 * This will inject the Stripe.js external library onto the page.
 * It will check if the script already exists and not mount it if it was found.
 **/
export async function addStripeTagToPage() {
  await loadScript(STRIPE_LIB_URL);
}
