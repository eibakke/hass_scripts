# Nordpool automation scheduling for Homeassistant
A collection of Homeassistant scripts that can be used for scheduling automations based on the price of electricity gotten from Nordpool.

This work is inspired by https://www.creatingsmarthome.com/index.php/2023/04/12/home-assistant-advanced-nord-pool-cheapest-hours-with-local-calendar-support they use the built in local calendar to schedule events the correspond to the desired actions. The calendar events are set based on user configuration and the energy prices from Nordpool.

## Setup

### Prerequisites
1. A running Homeassistant instance. [Official getting started guide](https://www.home-assistant.io/getting-started/). 
1. Enable and setup Python scripts in Homeassistant following the [official HASS guide](https://www.home-assistant.io/integrations/python_script/).
1. Install Homeassistant's [Local Calendar](https://www.home-assistant.io/integrations/local_calendar/) integration.
1. Install the Home Assistant Community Store ([HACS](https://hacs.xyz/)).
1. Install the [Nordpool HACS integration](https://github.com/custom-components/nordpool).

### Python scripts
The bulk of the work to create automation schedules happens in the Python scripts in this repository. There is one script for each type of automation and one script that runs every time a calendar event starts and ends, which triggers the event in the desription of the calendar event. You'll need to have the latter of these scripts installed for your automations to work.

1. Copy the `calendar_automations.py` script to your Python scripts folder. (Likely `<HASS_config_dir>/python_scripts`)
1. Copy the automation scripts for the scheduling types you want to use to your Python scripts folder.

### YAML configurations
I've put examples of the YAML configurations you could have in the `config_examples` directory in the repository. There you will find example configurations for the Homeassistant in general (mostly boilerplate and prerequisites) and for the scheduling automation scripts. There are examples for every type of automation scheduling and for the calendar automation schedule too.

For your installation you could start off with a copy of the example configuration and modify it to your needs.

### Debugging
The configuration example has the scheduling trigger every hour, and if you have logging enabled (see the `hass_config_example.yaml` file for how to enable this) you can follow along in the logs when the script runs. Errors and success messages should show up there if you have it set up as described here.

## Scheduling types

### Fixed sequence length scheduling
The first type of scheduling lets you schedule a certain number of sequences of a fixed length, with a given minimum distance between them. Just like the blog post that inspired it, you can schedule for today and tomorrow, and you have a fail safe that will kick in at a given time if the prices aren't available yet. New features from the blog post include the ability to schedule multiple sequences, the ability to schedule them a given distance apart, and simpler configuration. Below is an example configuration for a water heater to be on for 3 1 hour sequences a day, at least 6 hours apart:

```
    # To add scheduling for other devices, simple add another call to the cheapest_hours_energy service.
    - service: python_script.cheapest_hours_energy
      data:
        number_of_sequential_hours: 1
        number_of_sequences: 3
        min_hours_between_sequences: 6
        service_to_call: 'switch'
        start_method: 'turn_on'
        end_method: 'turn_off'
        automate_entity_id: 'switch.waterheater'
```

# In Progress
## Variable length sequences max hours apart
Say you'd like to ensure that your waterheater is on at least one hour in every four, and you'd like it to be on for 10 hours a day in total. This could easily lead to variable length sequences. With the configuration below, your water heater will be on for 8 hours a day, and there will be no gap where there is more than 12 hours without the waterheater being on. This means that even if the cheapest 8 hours are all in the early morning, the script will schedule one of the 8 hours such that there is not 12 consecutive hours where the water heater is off. In this case, that means will schedule 7 hours between 0 and 7, and one hour between 12 and 23. The solution is not yet quite optimal and is missing a few features like the option to include today's prices, so this is still in progress for now.

```
    # To add scheduling for other devices, simple add another call to the python_script.cheapest_non_sequential service.
    - service: python_script.cheapest_non_sequential
      data:
        max_hours_between_sequences: 12
        number_of_hours: 8
        service_to_call: switch
        start_method: turn_on
        end_method: turn_off
        automate_entity_id: switch.waterheater
```

# Not yet implemented

## Cheapest percentiles
Schedule something to be on for the bottom n% of hours. Say, only charge a battery for the 50% cheapest hours of the day.

