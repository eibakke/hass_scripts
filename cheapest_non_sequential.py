# Creates calendar events for the n cheapest hours of the day spaced a maximum distance apart.

# Arguments that have IDs for entities needed:
nordpool_sensor_id = data.get("nordpool_sensor_id", "sensor.nordpool_kwh_krsand_nok_3_10_025")
calendar_entity_id = data.get("calendar_entity_id", "calendar.electricity")

# Arguments that define the service, method, and entity to execute on start and end:
service_to_call = data.get("service_to_call")
start_method = data.get("start_method")
end_method = data.get("end_method")
automate_entity_id = data.get("automate_entity_id")

# Arguments that define the area to search within:
include_todays_prices = data.get("include_todays_prices", False)
search_start_hour_flag = data.get("search_start_hour", 0)
search_end_hour_flag = data.get("search_end_hour", 23)

# Arguments that define what type of sequences to search for:
number_of_hours = data.get("number_of_hours", 6)
max_hours_between_sequences = data.get("max_hours_between_sequences", 7)

fail_safe_hour = data.get("fail_safe_hour", 23)


# initialSchedule takes a list of sequences and a number of hours
# and returns a schedule consisting of the cheapest n hours.
# A schedule consists of a list of sequences.
def initialSchedule(sequences, hours):
  return sorted(sequences, key=lambda s: s[1])[:hours]


# hourlyPricesToSequences takes a list of prices indexed by hour,
# and the start_date of the first hour. The sequences returned
# are tuples of the format:
# ((start_date_time, end_date_time), price).
def hourlyPricesToSequences(hourly_prices, start_date_time):
  sequences = []
  for hour in range(0, len(hourly_prices)):
    seq_start_date_time = start_date_time + datetime.timedelta(hours=hour)
    seq_end_date_time = seq_start_date_time + datetime.timedelta(hours=1)
    sequences.append(((seq_start_date_time, seq_end_date_time), hourly_prices[hour])) 
  return sequences


# minimumHoursToCoverTimespans takes a number representing the max number of hours between
# sequences and returns the minimum number of hours that need to be scheduled in
# order to cover the entire day. Assuming that the shortest possible sequence is 1
# hour long.
def minimumHoursToCoverTimespans(timespans, max_gap):
  return len(timespans)//(max_gap+1)


def generatePossibleSchedules(sequences, max_gap):
  min_hrs = minimumHoursToCoverTimespans(sequences, max_gap)
  if min_hrs == 0:
    return []
  possible_schedules = []
  if min_hrs == 1:
    min_index = (len(sequences)-1) - max_gap
    max_index = max_gap+1
    for t in sequences[min_index:max_index]:
      possible_schedules.append([t]) 
    return possible_schedules
  for i in range(max_gap+1):
    rest = sequences[i+1:]
    if minimumHoursToCoverTimespans(rest, max_gap) <= (min_hrs-1):
      for p in generatePossibleSchedules(sequences[i+1:], max_gap):
        possible_schedules.append([sequences[i]] + p)
  return possible_schedules


def priceOfSequences(sequences):
  return sum([s[1] for s in sequences])


def cheapestPossibleScheduleInSequence(seqs, max_gap):
  possible_schedules = generatePossibleSchedules(seqs, max_gap)
  cheapest_price = 999
  cheapest_schedule = []
  for s in possible_schedules:
    p = priceOfSequences(s)
    if p < cheapest_price:
      cheapest_schedule = s
      cheapest_price = p
  return cheapest_schedule

# mergeNeighboringSequences takes a list of non-overlapping sequences and merges
# any sequences that are immediately after one another.
def mergeNeighboringSequences(seqs):
  seqs = sorted(seqs, key=lambda s: s[0][0])
  # a list of lists of sequences that are next to each other
  sequential_seqs = []
  merged_seqs = []
  curr_s = seqs[0]
  i = 1
  while i < len(seqs):
    next_s = seqs[i]
    if curr_s[0][1].hour == next_s[0][0].hour:
      p = (curr_s[1] + next_s[1]) / (next_s[0][1].hour - curr_s[0][0].hour)
      curr_s = ((curr_s[0][0], next_s[0][1]), p)
    else:
      merged_seqs.append(curr_s)
      curr_s = next_s
    i = i+1
  merged_seqs.append(curr_s)
  return merged_seqs


# createEventsForSequences takes the entity_id of a calendar
# and a list of sequences and creates events for those
def createEventsForSequences(calendar_id, sequences):
  desc = ":".join([service_to_call, start_method, end_method, automate_entity_id])
  logger.info("Creating calendar event with description: {}".format(desc))
  for seq, price in sequences:
    hass.services.call("calendar",
                       "create_event",
                       {"entity_id": calendar_id,
                        "start_date_time": str(seq[0]),
                        "end_date_time": str(seq[1]),
                        "summary": "[Nordpool automation: {}] Average hourly price: {}".format(automate_entity_id, price),
                        "description": desc})


nordpool_sensor = hass.states.get(nordpool_sensor_id)
hourly_prices = nordpool_sensor.attributes.get("tomorrow")
if hourly_prices is None or len(hourly_prices) == 0:
  raise Exception("No prices available yet")

start_date_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
sequences = hourlyPricesToSequences(hourly_prices, start_date_time)

logger.info("Prices: {}".format(hourly_prices))

min_hours = minimumHoursToCoverTimespans(hourly_prices, max_hours_between_sequences)
if number_of_hours < min_hours:
  logger.warning("Too few hours to cover the day with that gap. Proceeding with the minimum needed: {}".format(min_hours))
  number_of_hours = min_hours

# These are the hours that are more than what's needed for covering the day
# They will be placed on the cheapest hours of the day, and this will be the
# starting point for the rest of the schedule.
extra_hours = number_of_hours - min_hours

# First we get the cheapest "extra_hours" hours into our schedule:
schedule = initialSchedule(sequences, extra_hours)

# Next we schedule the remaining hours in the gaps that remain from
# scheduling the cheapest hours, such that no gap is larger than the
# predetermined limit:
hours_scheduled = sorted([s[0][0].hour for s in schedule])
logger.info("Initial hours_scheduled: {}".format(hours_scheduled))

i = 0
additional_sequences = []
for hr in hours_scheduled:
  seqs = sequences[i:hr]
  if len(seqs) > max_hours_between_sequences:
    additional_sequences.extend(cheapestPossibleScheduleInSequence(seqs, max_hours_between_sequences))
  i = hr+1

if len(hours_scheduled) == 0 or len(sequences) - hours_scheduled[-1] > max_hours_between_sequences:
  additional_sequences.extend(cheapestPossibleScheduleInSequence(sequences[i:len(sequences)], max_hours_between_sequences))

schedule.extend(additional_sequences)
hours_scheduled = sorted([s[0][0].hour for s in schedule])
logger.info("Schedule: {}".format(hours_scheduled))

# At this point we have scheduled the cheapest hours, and we know we have no gaps larger than allowed.
# However, there may still be some hours left to schedule, depending on how we have done the
# scheduling so far. We now place these hours that we have left on the cheapest remaining hours of the
# day:
if len(schedule) < number_of_hours:
  remaining_hours = number_of_hours - len(schedule)
  hours_scheduled_set = set(hours_scheduled)
  remaining_seqs = [s for s in sequences if s[0][0].hour not in hours_scheduled_set]
  schedule.extend(sorted(remaining_seqs, key=lambda s: s[1])[:remaining_hours])

hours_scheduled = sorted([s[0][0].hour for s in schedule])
logger.info("Final schedule: {}".format(hours_scheduled))

# TODO(eibakke): This setup does not actually find the optimal solution, because the number of "extra hours" changes after the initial scheduling
# an improvement would be to recalculate the number of "extra hours" after the initial scheduling, schedule those on the cheapest hours, and repeat
# until there are no more "extra hours".
schedule = mergeNeighboringSequences(schedule)
logger.info("Merged schedule: {}".format(schedule))

createEventsForSequences(calendar_entity_id, schedule)
