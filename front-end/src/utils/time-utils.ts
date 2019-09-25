import moment from 'moment';

export function getFriendlyDurationSinceString(time: number) {
  return moment.duration(-moment().diff(time)).humanize(true);
}
