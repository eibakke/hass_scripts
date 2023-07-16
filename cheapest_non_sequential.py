# Creates calendar events for the n cheapest hours of the day spaced a maximum distance apart.

# Arguments that have IDs for entities needed:
nordpool_sensor_id = data.get("nordpool_sensor_id", "sensor.nordpool_kwh_krsand_nok_3_10_025")
calendar_entity_id = data.get("calendar_entity_id", "calendar.electricity")
cheapest_hours_set_bool = data.get("cheapest_hours_set_bool", "input_boolean.cheapest_hours_set")

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
number_of_hours_flag = data.get("number_of_hours", 6)
max_hours_between_sequences = data.get("max_hours_between_sequences", 7)

fail_safe_hour = data.get("fail_safe_hour", 23)

test_run = data.get("test_run", False) # when true schedule will be logged and cheapest_hours_set_bool will be ignored

# scheduleCheapestHoursInList takes a list of sequences and a number of hours
# and returns a schedule consisting of the cheapest n hours.
# A schedule consists of a list of sequences.
def scheduleCheapestHoursInList(sequences, hours):
  return sorted(sequences, key=lambda s: s[1])[:hours]


# gapsInSchedule takes a full sequence of hours to make a schedule in and a
# schedule of hours from the hours in that sequence. It returns the unscheduled
# hours from that sequence as a list. For example:
# sequence: [0, 1, 2, 3, 4, 5]
# schedule: [2, 5]
# gaps returned: [[0, 1], [3, 4]]
def gapsInSchedule(sequences, schedule):
  gaps = []
  hours_scheduled = sorted([s[0][0].hour for s in schedule])

  i = 0
  for hr in hours_scheduled:
    gaps.append(sequences[i:hr])
    i = hr+1

  if len(hours_scheduled) == 0 or len(sequences) - hours_scheduled[-1] > 0:
    gaps.append(sequences[i:len(sequences)])
  return gaps


# removeScheduledHours takes a list of sequences and a schedule made up of hours
# from those sequences and returns a list of hours that does not contain the
# scheduled hours.
def removeScheduledHours(sequences, schedule):
  remaining_hours = []
  schedule_set = set(schedule)
  for h in sequences:
    if h in schedule_set:
      continue
    remaining_hours.append(h)
  return remaining_hours


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


# generatePossibleSchedules takes a list of hourly prices and a maximum
# number of hours where there can be no hours scheduled, and returns
# all the possible combinations of hours that satisfy the condition.
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


# cheapestPossibleScheduleInSequences takes a list of hourly prices and a
# maximum number of hours where there can be no hours scheduled, and returns
# the cheapest sequence of hours.
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
  sum_p = curr_s[1]
  i = 1
  while i < len(seqs):
    next_s = seqs[i]
    if curr_s[0][1].hour == next_s[0][0].hour:
      sum_p = sum_p + next_s[1]
      curr_s = ((curr_s[0][0], next_s[0][1]), curr_s[1])
    else:
      p = sum_p / (curr_s[0][1].hour - curr_s[0][0].hour)
      sum_p = next_s[1]
      merged_seqs.append(((curr_s[0][0], curr_s[0][1]), p))
      curr_s = next_s
    i = i+1
  p = sum_p / (curr_s[0][1].hour - curr_s[0][0].hour)
  merged_seqs.append(((curr_s[0][0], curr_s[0][1]), p))
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


def getHourlyPrices():
  nordpool_sensor = hass.states.get(nordpool_sensor_id)
  fail_safe_time = datetime.datetime.now().replace(hour=fail_safe_hour, minute=0, second=0, microsecond=0)

  # The Python runtime gets confused about search_start_hour and end_hour looking like local vars not global vars so we just do a little reassignment here.
  search_start_hour = search_start_hour_flag
  search_end_hour = search_end_hour_flag
  
  start_date_time = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

  hourly_prices = []
  if nordpool_sensor.attributes.get("tomorrow_valid"):
    hourly_prices = nordpool_sensor.attributes.get("tomorrow")
    if include_todays_prices:
      hourly_prices = nordpool_sensor.attributes.get("today") + hourly_prices
      start_date_time = start_date_time - datetime.timedelta(days=1)
      search_end_hour = search_end_hour + len(nordpool_sensor.attributes.get("today"))
  elif fail_safe_time < datetime.datetime.now():
    hourly_prices = [0] * 24

  if hourly_prices is None or len(hourly_prices) == 0:
    raise Exception("No prices available yet")
  
  sequences = hourlyPricesToSequences(hourly_prices, start_date_time)
  return sequences[search_start_hour:search_end_hour+1]


def setCheapestHours():
  sequences = getHourlyPrices()

  number_of_hours = number_of_hours_flag
  min_hours = minimumHoursToCoverTimespans(sequences, max_hours_between_sequences)
  if number_of_hours < min_hours:
    logger.warning("Too few hours to cover the day with that gap. Proceeding with the minimum needed: {}".format(min_hours))
    number_of_hours = min_hours

  schedule = []
  remaining_sequences = sequences
  # These are the hours that are more than what's needed for covering the day
  # They will be placed on the cheapest hours of the day, and this will be the
  # starting point for the rest of the schedule.
  extra_hours = number_of_hours - min_hours
  while extra_hours > 0:
    # First we get the cheapest "extra_hours" hours into our schedule:
    schedule.extend(scheduleCheapestHoursInList(remaining_sequences, extra_hours))
    remaining_sequences = removeScheduledHours(remaining_sequences, schedule)
    gaps = gapsInSchedule(sequences, schedule)
    min_hours = 0
    for g in gaps:
      min_hours = min_hours + minimumHoursToCoverTimespans(g, max_hours_between_sequences)
    extra_hours = number_of_hours - len(schedule) - min_hours

  # Next we schedule the remaining hours in the gaps that remain from
  # scheduling the cheapest hours, such that no gap is larger than the
  # predetermined limit:
  hours_scheduled = sorted([s[0][0].hour for s in schedule])
  logger.info("Initial hours_scheduled: {}".format(hours_scheduled))

  gaps = gapsInSchedule(sequences, schedule)
  for gap in gaps:
    if len(gap) > max_hours_between_sequences:
      schedule.extend(cheapestPossibleScheduleInSequence(gap, max_hours_between_sequences))

  hours_scheduled = sorted([s[0][0].hour for s in schedule])
  logger.info("Final schedule: {}".format(hours_scheduled))

  schedule = mergeNeighboringSequences(schedule)
  logger.info("Merged schedule: {}".format(schedule))

  if not test_run:
    createEventsForSequences(calendar_entity_id, schedule)
    hass.services.call("input_boolean", "turn_on", {"entity_id": cheapest_hours_set_bool})


# validateFlags raises a ValueError if flags that don't have defaults,
# but still are required are not set.
def validateFlags():
  if service_to_call is None or service_to_call == "":
    raise ValueError("service_to_call must be set")
  if start_method is None or start_method == "":
    raise ValueError("start_method must be set")
  if end_method is None or end_method == "":
    raise ValueError("end_method must be set")
  if automate_entity_id is None or automate_entity_id == "":
    raise ValueError("automate_entity_id must be set")


cheapest_hours_set = hass.states.get(cheapest_hours_set_bool)
if cheapest_hours_set.state == "off" or test_run:
  validateFlags()
  setCheapestHours()

