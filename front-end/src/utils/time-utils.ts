import moment, { Moment } from 'moment';

export function getFriendlyDurationSinceString(time: number | Moment) {
  return moment.duration(-moment().diff(time)).humanize(true);
}
