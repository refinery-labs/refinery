import { formatDistanceToNow, fromUnixTime } from 'date-fns';

export function getFriendlyDurationSinceString(time: number) {
  return formatDistanceToNow(fromUnixTime(time / 1000)) + ' ago';
}
