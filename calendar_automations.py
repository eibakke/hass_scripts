# This script gets events that are on the calendar around now and acts on the actions in the descriptions.
event = data.get("event")
calendar_event = data.get("calendar_event")

if calendar_event != None and calendar_event["description"] != "":
  service, start_method, end_method, entity_id = calendar_event["description"].split(":")

  method = ""
  if event == "start":
    method = start_method
  elif event == "end":
    method = end_method

  logger.info("Executing {}.{} on entity: {}".format(service, method, entity_id))
  hass.services.call(service, method, {"entity_id": entity_id})

