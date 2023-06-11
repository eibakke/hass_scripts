# Automations for Homeassistant
Most of these automations use prices from Nordpool to optimize energy usage. They are inspired by https://www.creatingsmarthome.com/index.php/2023/04/12/home-assistant-advanced-nord-pool-cheapest-hours-with-local-calendar-support they use the built in local calendar to schedule events the correspond to the desired actions. The calendar events are set based on user configuration and the energy prices from Nordpool. There are several ways to do this, and the following are implemented here:

## Fixed sequence length scheduling
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

