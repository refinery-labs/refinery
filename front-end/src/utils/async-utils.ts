export function timeout(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export interface AutoRefreshJobConfig {
  nonce: string;
  timeoutMs: number;
  maxIterations: number;
  makeRequest: () => Promise<void>;
  isStillValid: (nonce: string, iteration: number) => Promise<boolean>;
  onComplete?: (timeout: boolean) => Promise<void>;
}

/**
 * Job to go do something on an interval. Attempts to kill itself by leveraging callbacks for state checking.
 * @param conf Parameters for the job to function.
 * @param iterations Incremented each time and used to kill itself later by limiting max iterations.
 */
export async function autoRefreshJob(conf: AutoRefreshJobConfig, iterations: number = 0) {
  if (iterations > conf.maxIterations) {
    conf.onComplete && (await conf.onComplete(true));
    return;
  }

  const valid = await conf.isStillValid(conf.nonce, iterations);

  if (!valid) {
    conf.onComplete && (await conf.onComplete(false));
    return;
  }

  await conf.makeRequest();

  await timeout(conf.timeoutMs);

  await autoRefreshJob(conf, iterations + 1);
}

export async function waitUntil(
  intervalMs: number,
  maxIntervals: number,
  maintainIfTrue: () => boolean
): Promise<boolean> {
  // Wait until the function says false
  for (let i = 0; i < maxIntervals; i++) {
    if (!maintainIfTrue()) {
      // We did not time out
      return false;
    }
    await timeout(intervalMs);
  }

  // We hit our timeout
  return true;
}
