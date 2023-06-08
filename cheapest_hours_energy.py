# Creates a calendar event for the n cheapest hours of the day given a series of prices retrieved from a Nordpool sensor.

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
number_of_sequential_hours = data.get("number_of_sequential_hours", 1)
number_of_sequences = data.get("number_of_sequences", 1)
min_hours_between_sequences = data.get("min_hours_between_sequences", 0)

fail_safe_hour = data.get("fail_safe_hour", 23)


# hourlyPricesToSequences takes a list of prices indexed by hour,
# the length of the sequences to build, and the start_date of the
# first hour. The sequences returned are tuples of the format
# ((start_date_time, end_date_time), average_price).
def hourlyPricesToSequences(hourly_prices, sequence_length, start_date_time):
  sequences = []
  for hour in range(0, len(hourly_prices) - sequence_length):
    seq_start_date_time = start_date_time + datetime.timedelta(hours=hour)
    seq_end_date_time = seq_start_date_time + datetime.timedelta(hours=sequence_length)
    sequences.append(((seq_start_date_time, seq_end_date_time), sum(hourly_prices[hour:hour+sequence_length]) / sequence_length))
  return sequences


# cheapestNSequentialHours takes a list of sequences of
# the same length, and two positive integers:
# number_of_sequences and hours_between. It returns
# a list number_of_sequences cheapest sequences that are
# at least hours_between hours apart. 
# 
# Note that this does not guarantee the cheapest possible
# configuration over all, as it implements a greedy
# approach that always selects the cheapest sequence first.
def cheapestNSequentialHours(sequences, number_of_sequences, hours_between):
  sorted_sequences = sorted(sequences, key=lambda s: s[1])
  non_overlapping_sequences = []
  sequences_to_return = []
  for seq in sorted_sequences:
    if sequenceOverlapsAny(seq, non_overlapping_sequences):
      continue
    non_overlapping_sequences.append(((seq[0][0]-datetime.timedelta(hours=hours_between), seq[0][1]+datetime.timedelta(hours=hours_between)), seq[1]))
    sequences_to_return.append(seq)
  return sequences_to_return[:number_of_sequences]


# sequenceOverlapsAny takes a single sequence and a list
# of sequences. If the single sequence overlaps any of
# the sequences in the list, it returns True. Otherwise
# it returns False.
def sequenceOverlapsAny(seq, seqs):
  for s in seqs:
    if sequencesOverlap(seq, s):
      return True
  return False


# sequencesOverlap takes two sequences and returns true if
# if they overlap.
def sequencesOverlap(seq1, seq2):
  # We know the sequences are the same length and that they
  # are not the exact same sequence. This means there are 
  # only two possibilities for overlap:
  # 1. seq1 [] starts in the middle of seq2 {}: {  [  }  ]
  if seq2[0][0] < seq1[0][0] and seq1[0][0] < seq2[0][1]:
    return True
  # 2. seq1 [] ends in the middle of seq2 {}:   [  {  ]  }
  if seq2[0][0] < seq1[0][1] and seq1[0][1] < seq2[0][1]:
    return True
  return False


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


def setCheapestHours():
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

  logger.info("Looking for the cheapest sequences in: {}".format(hourly_prices))
  if len(hourly_prices) != 0:
    sequences = hourlyPricesToSequences(hourly_prices, number_of_sequential_hours, start_date_time)
    sequences = sequences[search_start_hour:search_end_hour+1]
    cheapest_n_seqs = cheapestNSequentialHours(sequences, number_of_sequences, min_hours_between_sequences)
    createEventsForSequences(calendar_entity_id, cheapest_n_seqs)

setCheapestHours()

