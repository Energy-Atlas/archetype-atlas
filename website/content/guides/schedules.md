# Inspect schedules

A program page renders every schedule it uses; a folder page renders the schedules of
its services and systems.

- **Rule schedules** list their rules in source order (dates, day types, rule type and
  the day profile they use) and then each distinct 24-hour day profile as a step plot
  with its exact values. The last matching specific rule wins, then the default.
  Wrapped seasons, holidays and design days keep their source meaning; nothing is
  compiled into an annual calendar.
- **Annual schedules** (ResStock dwellings, 8,760 hourly values) show the monthly mean
  and the typical day (the mean of each hour over the year) as plots and tables. The
  hourly values are not tabulated; the schedule's **JSON** holds the complete series
  with its recorded calendar, seed and weather.
- A constant zero slot (`{"constant": 0}`) is stated on the load, not as a schedule.

Plots are inline SVG drawn when the site is built, so they read without JavaScript.
