# Automations for Homeassistant
Most of these automations use prices from Nordpool to optimize energy usage. They are inspired by https://www.creatingsmarthome.com/index.php/2023/04/12/home-assistant-advanced-nord-pool-cheapest-hours-with-local-calendar-support they use the built in local calendar to schedule events the correspond to the desired actions. The calendar events are set based on user configuration and the energy prices from Nordpool. There are several ways to do this, and the following are implemented here:

## Fixed sequence length scheduling
The first type of scheduling lets you schedule a certain number of sequences of a fixed length, with a given minimum distance between them. Just like the blog post that inspired it, you can schedule for today and tomorrow, and you have a fail safe that will kick in at a given time if the prices aren't available yet. New features from the blog post include the ability to schedule multiple sequences, the ability to schedule them a given distance apart, and simpler configuration. Below is an example configuration for a water heater to be on for 3 1 hour sequences a day, at least 6 hours apart:

```
automation:
  # Make call a call to the energy service every hour
  - id: 'cheapest_hours_set_sequence'
    alias: 'Cheapest hours: Set next cheapest sequence'
    description: 'Checks tomorrow energy prices every hour and create calendar entry when available AND events not yet created'
    trigger:
    - platform: time_pattern
      hours: /1
    action:
    # To add scheduling for other devices, simple add another call to the cheapest_hours_energy service.
    - service: python_script.cheapest_hours_energy
      data:
        service_to_call: 'switch'
        start_method: 'turn_on'
        end_method: 'turn_off'
        automate_entity_id: 'switch.waterheater'
        number_of_sequential_hours: 1
        number_of_sequences: 3
        min_hours_between_sequences: 6
        cheapest_hours_set_bool: 'input_boolean.cheapest_hours_set'
        fail_safe_hour: 23
    # Make sure this service is the last to be called. Since actions are called in sequence we need this
    # to run only after all the other automations have succeeded.
    - service: input_boolean.turn_on
      data: {}
      target:
        entity_id: input_boolean.cheapest_hours_set
    mode: single

  # Triggers when a calendar event starts or ends and passes the whole event to the automation script
  - id: 'calendar_event_trigger'
    alias: 'Passes calendar event to script'
    description: ''
    trigger:
    - platform: calendar
      event: start
      entity_id: calendar.electricity
    - platform: calendar
      event: end
      entity_id: calendar.electricity
    action:
    - service: python_script.calendar_automations
      data:
        calendar_event: '{{ trigger.calendar_event }}'
        event: '{{ trigger.event }}'
    mode: single 

  # Resets the cheapest_hours_set flag at a given time.
  - id: 'cheapest_hours_clear_set_flag'
    alias: 'Cheapest hours: Reset the set helper for the next day'
    description: 'Clears cheapest hours helper boolean when the day changes.'
    trigger:
    - platform: time
      at: '01:15:00'
    condition: []
    action:
    - service: input_boolean.turn_off
      data: {}
      target:
        entity_id: input_boolean.cheapest_hours_set
    mode: single

# A flag to determine if the cheapest_hours_set_sequence has successfully run yet.
input_boolean:
  cheapest_hours_set:
    name: Cheapest hours set for the next day
    icon: mdi:clock


